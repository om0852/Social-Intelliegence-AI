import { Scraper } from './scraper.js';
import { SearchManager } from './search.js';
import { AIService } from './ai.js';

export class Orchestrator {
    constructor() {
        this.scraper = new Scraper();
        this.searchManager = new SearchManager();
        this.aiService = new AIService();
    }

    async runPipeline(url) {
        console.log(`--- Phase 1: Scraping ${url} ---`);
        const article = await this.scraper.scrape(url);
        
        console.log(`--- Phase 2: AI Analyzing Article ---`);
        const extracted = await this.aiService.analyzeArticle(article);
        
        console.log(`--- Phase 3: Search Enrichment (Social Profiles) ---`);
        if (extracted.author_name) {
            const profiles = await this.searchManager.findSocialProfiles(
                extracted.author_name, 
                extracted.company_name || extracted.platform
            );
            extracted.social_profiles = profiles;
        }

        console.log(`--- Phase 4: Final Synthesis ---`);
        const finalized = await this.aiService.synthesize(extracted, article.content);
        
        return finalized;
    }
}
