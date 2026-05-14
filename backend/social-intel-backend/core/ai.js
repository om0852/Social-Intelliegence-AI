import axios from 'axios';
import dotenv from 'dotenv';

dotenv.config({ path: '../.env' });

export class AIService {
    constructor() {
        this.apiKey = process.env.GEMINI_API_KEY;
        this.baseUrl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent";
    }

    async _callAI(prompt) {
        try {
            const response = await axios.post(`${this.baseUrl}?key=${this.apiKey}`, {
                contents: [{ parts: [{ text: prompt }] }]
            });
            const text = response.data.candidates[0].content.parts[0].text;
            // Clean up JSON if LLM adds markdown
            return text.replace(/```json|```/g, '').trim();
        } catch (error) {
            console.error(`[AI] Error:`, error.response?.data || error.message);
            throw new Error("AI Processing failed");
        }
    }

    async analyzeArticle(article) {
        const prompt = `
        Analyze this article and extract metadata in JSON format:
        Article Title: ${article.title}
        Content: ${article.content}

        JSON Structure:
        {
          "title": "Article Title",
          "description": "Short summary",
          "author_name": "Name of the person who wrote it",
          "company_name": "Author's company or organization",
          "platform": "The website name",
          "location": {"city": null, "state": null, "country": null},
          "age": null
        }
        `;
        const result = await this._callAI(prompt);
        return JSON.parse(result);
    }

    async synthesize(metadata, content) {
        const prompt = `
        Refine the following metadata based on the full article content. 
        If age or location is mentioned, include it.
        Metadata: ${JSON.stringify(metadata)}
        Content Snippet: ${content.substring(0, 2000)}

        Return the final JSON object.
        `;
        const result = await this._callAI(prompt);
        return JSON.parse(result);
    }
}
