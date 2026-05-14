import os
import json
import logging
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from groq import Groq
from google import genai
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SocialProfile(BaseModel):
    url: str
    platform: str
    username: Optional[str] = None
    followers: Optional[int] = 0
    bio: Optional[str] = None

class Location(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None

class InitialExtraction(BaseModel):
    title: str
    description: str
    author_name: Optional[str] = None
    author_username: Optional[str] = None
    company_name: Optional[str] = None
    publisher: Optional[str] = None
    platform: Optional[str] = None
    profile_url: Optional[str] = None
    social_profiles: List[str] = []

class CountryShare(BaseModel):
    country: str
    share: float

class Keyword(BaseModel):
    name: str
    estimated_value: float
    volume: int

class DomainMetrics(BaseModel):
    site_name: Optional[str] = None
    site_description: Optional[str] = None
    global_rank: Optional[int] = 0
    country_rank: Optional[int] = 0
    category: Optional[str] = None
    category_rank: Optional[int] = 0
    total_visits: Optional[str] = "0"
    bounce_rate: Optional[float] = 0.0
    pages_per_visit: Optional[float] = 0.0
    avg_visit_duration: Optional[str] = "0:00"
    top_countries: List[CountryShare] = []
    traffic_sources: Dict[str, float] = {}
    estimated_monthly_visits: Dict[str, int] = {}
    top_keywords: List[Keyword] = []

class AuthorDemographics(BaseModel):
    gender: Optional[str] = "Unknown"
    industry: Optional[str] = "Unknown"
    seniority: Optional[str] = "Unknown"
    interests: List[str] = []
    estimated_experience: Optional[str] = "Unknown"

class FinalIntelligence(BaseModel):
    title: str
    description: str
    author_name: Optional[str] = None
    author_username: Optional[str] = None
    author_demographics: Optional[AuthorDemographics] = None
    platform: Optional[str] = None
    followers: Optional[int] = 0
    age: Optional[int] = 0
    company_name: Optional[str] = None
    location: Location
    social_profiles: List[SocialProfile] = []
    domain_metrics: Optional[DomainMetrics] = None

class IntelligenceEngine:
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

    async def analyze_initial(self, url: str, text: str, profile_links: List[dict] = []) -> InitialExtraction:
        """
        Phase 2: Identify author and look for profile links.
        """
        links_context = "\n".join([f"- {l['text']}: {l['href']}" for l in profile_links])
        
        prompt = f"""
        You are an expert data extractor. Analyze the content from this URL: {url}
        
        EXTRACT:
        1. Title and a brief description.
        2. Author Name: The person who WROTE or POSTED the content.
           - For interviews (e.g., "In Conversation with X"), the author is the INTERVIEWER, not the person being interviewed.
           - On social media (Reddit, Twitter/X), this is the User who created the post.
        3. Author Username/Handle (e.g. @name, u/name).
        4. Company/Organization Name (The company/subject the article is ABOUT).
        5. Publisher Name (The organization that originally published the content, e.g. Times of India, BW Legal World).
        6. Platform (The site you are currently on, e.g. Reddit, Twitter, Medium, News Site).
        
        CRITICAL: Select the most likely Author Profile URL from the following list or find it in the text.
        If it's a social platform, prioritize the user profile link:
        {links_context}
        
        Return ONLY valid JSON matching this structure:
        {{
            "title": "string",
            "description": "string",
            "author_name": "string or null",
            "author_username": "string or null",
            "company_name": "string or null",
            "publisher": "string or null",
            "platform": "string or null",
            "profile_url": "string or null"
        }}

        CONTENT:
        {text[:15000]}
        """
        
        return await self._call_llm(prompt, InitialExtraction)

    async def finalize_data(self, base: InitialExtraction, enriched_text: Optional[str] = None) -> FinalIntelligence:
        """
        Phase 4: Merge base data with enriched profile data and resolve location.
        """
        prompt = f"""
        Analyze the following article data and social media profile snippets to create a FINAL enrichment report for the author.
        
        ARTICLE INFO:
        Title: {base.title}
        Initial Description: {base.description}
        Publisher/Platform: {base.platform}
        
        SOCIAL ENRICHMENT DATA:
        {enriched_text if enriched_text else "No additional social data found."}
        
        TASK:
        1. Refine the author's full name, current company, and location.
        2. Extract EXACT follower counts for each platform (LinkedIn, X, Instagram, etc.).
        3. **INFER AUTHOR DEMOGRAPHICS**:
           - Industry: What is their primary professional field? (e.g. "Legal Journalism")
           - Seniority: Are they an Executive, Manager, Lead, or Individual?
           - Interests: List 3-5 core professional interests from their bio.
           - Experience: Estimate years of experience (e.g. "10+ years").
           - Gender: Infer based on name or bio pronouns.
        4. **ESTIMATE AGE**: If the exact age is not mentioned, ESTIMATE it based on career milestones (e.g. graduation year).
        5. Consolidate all social profile URLs found with their bio and followers.
        
        STRICT RULES:
        - Return ONLY a JSON object matching the 'FinalIntelligence' schema.
        - If multiple follower counts are found, use the HIGHEST count for the main 'followers' field.
        - Do NOT hallucinate metrics. Use 0 or "Unknown" if not found.
        - Ensure 'social_profiles' is a list of objects.
        """
        
        return await self._call_llm(prompt, FinalIntelligence)

    def _clean_json(self, text: str) -> str:
        """Strips markdown and cleans JSON text for parsing."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Remove any leading/trailing garbage that isn't { or [
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
            
        return text

    async def _call_llm(self, prompt: str, schema: type[BaseModel]) -> any:
        """Calls LLMs with a fallback chain and robust JSON parsing."""
        # Clean fallback list (removed decommissioned models)
        models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama3-70b-8192",
            "llama-3.1-8b-instant"
        ]

        # Try Groq models first
        for model_name in models:
            try:
                logger.info(f"Trying Groq Model: {model_name} (Temp: 0.0)")
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=model_name,
                    temperature=0.0,
                    response_format={"type": "json_object"} if "8b" not in model_name else None
                )
                raw_content = chat_completion.choices[0].message.content
                clean_content = self._clean_json(raw_content)
                
                try:
                    result = schema.model_validate_json(clean_content)
                except Exception as ve:
                    # JSON Repair: Sometimes 8b models wrap the result in an "author" or "data" key
                    logger.warning(f"Validation failed for {model_name}, attempting repair...")
                    data = json.loads(clean_content)
                    if "data" in data: data = data["data"]
                    if "author" in data and schema.__name__ == "FinalIntelligence":
                        # Flatten nested author data if found
                        author_data = data.pop("author")
                        data.update(author_data)
                    result = schema.model_validate(data)

                # Auto-resolve location if it's FinalIntelligence
                if isinstance(result, FinalIntelligence):
                    result.location = self.resolve_location(result.location)
                    # Final AI Cleanup for Geo
                    if result.location.city and not result.location.state:
                        result.location = self.ai_resolve_state(result.location)
                    
                return result

            except Exception as e:
                logger.warning(f"Groq Model {model_name} failed: {e}. Trying next fallback...")
                continue

        # Last resort: Gemini
        try:
            logger.info("All Groq models failed. Falling back to Gemini (Temp: 0.0)...")
            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.0
                }
            )
            data = json.loads(response.text)
            result = model_class(**data)
            
            if isinstance(result, FinalIntelligence):
                result.location = self.resolve_location(result.location)
                
            return result
        except Exception as e:
            logger.error(f"All LLMs failed (including Gemini): {e}")
            raise e

    def resolve_location(self, loc: Location) -> Location:
        """
        Uses Nominatim (OpenStreetMap) to resolve State/Country from City.
        """
        if not loc.city or (loc.state and loc.country):
            return loc
            
        try:
            geolocator = Nominatim(user_agent="social_intelligence_bot", timeout=10)
            query = f"{loc.city}"
            if loc.state: query += f", {loc.state}"
            if loc.country: query += f", {loc.country}"
            
            location = geolocator.geocode(query, addressdetails=True, language='en')
            if location and 'address' in location.raw:
                address = location.raw['address']
                print(f"DEBUG: Geo Address: {address}")
                loc.city = loc.city or address.get('city') or address.get('town') or address.get('village') or address.get('suburb')
                loc.state = loc.state or address.get('state') or address.get('state_district')
                loc.country = loc.country or address.get('country')
        except Exception as e:
            print(f"Geo Resolution failed: {e}")
            
        return loc

    def ai_resolve_state(self, loc: Location) -> Location:
        """
        Fallback: Ask Groq to resolve the state/country from city.
        """
        if not loc.city:
            return loc
            
        prompt = f"Given the city '{loc.city}', what is the state/province and country? Return ONLY JSON: {{\"city\": \"{loc.city}\", \"state\": \"...\", \"country\": \"...\"}}"
        try:
            chat = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant", 
                response_format={"type": "json_object"}
            )
            data = json.loads(chat.choices[0].message.content)
            print(f"DEBUG: AI Geo Resolution: {data}")
            loc.state = loc.state or data.get("state")
            loc.country = loc.country or data.get("country")
        except:
            pass
        return loc
