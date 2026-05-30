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
    following: Optional[int] = 0
    connections: Optional[int] = 0
    position: Optional[str] = "Unknown"
    experience: Optional[str] = "Unknown"
    bio: Optional[str] = None
    age: Optional[int] = 0
    gender: Optional[str] = "Unknown"
    location: Optional[str] = "Unknown"

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
    topic: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None

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
    position: Optional[str] = "Unknown"

class RadarLocation(BaseModel):
    country_code: str
    country_name: str
    traffic_share: float

class RadarTechnicalDemographics(BaseModel):
    device_desktop: float
    device_mobile: float
    device_tablet: float
    os_windows: float
    os_android: float
    os_ios: float
    os_mac: float
    os_linux: float
    browser_chrome: float
    browser_safari: float
    browser_firefox: float
    browser_edge: float
    human_traffic_share: float
    bot_traffic_share: float

class RadarIntelligence(BaseModel):
    top_locations: List[RadarLocation] = []
    audience_demographics: Optional[RadarTechnicalDemographics] = None

class FinalIntelligence(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    author_name: Optional[str] = None
    author_username: Optional[str] = None
    author_demographics: Optional[AuthorDemographics] = None
    platform: Optional[str] = None
    followers: Optional[int] = 0
    following: Optional[int] = 0
    age: Optional[int] = 0
    company_name: Optional[str] = None
    location: Location
    social_profiles: List[SocialProfile] = []
    domain_metrics: Optional[DomainMetrics] = None
    topic: Optional[str] = None
    category: Optional[str] = None
    sentiment: Optional[str] = None
    radar_metrics: Optional[RadarIntelligence] = None

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
        2. Author Name: The primary person of interest who wrote the content, posted it, or is the main subject being interviewed/profiled (e.g., in Q&As, interviews, or conversations, prioritize the interviewee/subject of the article over the reporter/journalist/editorial team).
        3. Author Username/Handle.
        4. Company/Organization Name associated with the primary person of interest (e.g. the company they work for or represent).
        5. Publisher Name (e.g. the website or news outlet).
        6. Platform.
        7. Topic: The main topic or theme discussed in the content.
        8. Category: The category of the topic (e.g. Technology, Legal, Finance, Healthcare, Lifestyle, etc.).
        9. Sentiment: The overall sentiment of the content (Positive, Neutral, Negative).
        
        STRICT RULES:
        - Return ONLY a JSON object matching the schema below.
        - DO NOT wrap the response in a parent key like "data" or "author".
        - Use "Unknown" if data is missing.
        
        {links_context}
        
        JSON STRUCTURE:
        {{
            "title": "string",
            "description": "string",
            "author_name": "string or null",
            "author_username": "string or null",
            "company_name": "string or null",
            "publisher": "string or null",
            "platform": "string or null",
            "profile_url": "string or null",
            "topic": "string or null",
            "category": "string or null",
            "sentiment": "string or null"
        }}

        CONTENT:
        {text[:15000]}
        """
        
        return await self._call_llm(prompt, InitialExtraction)

    async def finalize_data(self, base: InitialExtraction, enriched_text: Optional[str] = None) -> FinalIntelligence:
        """
        Phase 4: Merge base data with enriched profile data and resolve location.
        """
        # Truncate enrichment data to avoid Groq 413 Payload Too Large
        safe_enrichment = (enriched_text or "No additional social data found.")[:8000]
        
        prompt = f"""
        Analyze the following article data and social media profile snippets to create a FINAL enrichment report for the author/person of interest.
        
        INITIAL EXTRACTION:
        Author Name: {base.author_name}
        Author Username: {base.author_username}
        Company Name: {base.company_name}
        Publisher: {base.publisher}
        Platform: {base.platform}
        Original Profile URL: {base.profile_url}
        Topic: {base.topic}
        Category: {base.category}
        Sentiment: {base.sentiment}
        
        ARTICLE INFO:
        Title: {base.title}
        Description: {base.description}
        
        SOCIAL ENRICHMENT DATA:
        {safe_enrichment}
        
        STRICT RULES:
        1. Return ONLY a JSON object matching the 'FinalIntelligence' schema.
        2. DO NOT wrap the response in a parent key.
        3. Include the original 'title' and 'description' from the ARTICLE INFO above.
        4. Populate 'author_name' using the INITIAL EXTRACTION value unless the SOCIAL ENRICHMENT DATA provides a more accurate or complete name.
        5. Populate 'company_name' using the INITIAL EXTRACTION value or resolve it from the author's current organization mentioned in the social snippets.
        6. Preserve or refine 'topic', 'category', and 'sentiment' from the INITIAL EXTRACTION.
        7. For 'followers', extract/estimate the highest follower count found for the author across their profiles. It MUST be a single integer. If the snippet says '500+', use 500. If it says '1.5K', use 1500. Do NOT output '5' for '500+'.
        8. For 'following', extract/estimate the highest following count found for the author across their profiles. It MUST be a single integer.
        9. For 'age', estimate the author's/subject's age in years as an integer based on:
           - Explicit mentions of their age in their bios or snippets.
           - Their education/career timeline (e.g. if they started university in 2000, they were likely ~18 then, meaning they were born around 1982. Current year is 2026, so they would be approximately 44 years old. If they started their first job in 2010, they were likely ~22 then, meaning they were born around 1988, making them ~38 in 2026).
           - Do your best to estimate an approximate age if there are any professional timeline details in the snippets or article. If there is absolutely no timeline or age information, default to 0.
        10. Populate 'location' as an object containing {{"city": "...", "state": "...", "country": "..."}}. Use snippets or article info to find their location, or "Unknown" if not found.
        11. Populate 'author_demographics' with:
           - 'gender': "Male", "Female", "Non-binary", or "Unknown".
           - 'industry': The primary industry they work in (e.g., "Legal", "Technology", "Finance", etc.).
           - 'seniority': Their professional seniority level (e.g., "C-Level", "VP", "Director", "Senior", "Junior", "Unknown").
           - 'interests': A list of key professional/personal interests extracted from their bio or description.
           - 'estimated_experience': Estimate their years of professional experience (e.g., "10+ years", "15 years", "Unknown") based on their career history.
           - 'position': The job title or role of the author (e.g. "Chief Legal Officer", "Software Engineer", "Marketing Director").
        12. Populate 'social_profiles' by extracting a list of profile objects found in the snippets. ONLY extract profiles that belong EXACTLY to the main Author/Company described in the INITIAL EXTRACTION. Do NOT extract profiles of employees, staff, or other related individuals. Each profile object must match the SocialProfile schema:
            {{
                "url": "string", 
                "platform": "string", 
                "username": "string or null", 
                "followers": int, 
                "following": int, 
                "connections": int, 
                "position": "string or Unknown", 
                "experience": "string or Unknown", 
                "bio": "string or null", 
                "age": int, 
                "gender": "string or Unknown", 
                "location": "string or Unknown"
            }}
            Ensure that 'followers', 'following', and 'connections' are accurate integers (e.g. 500 for '500+', NOT 5).
        """
        
        result = await self._call_llm(prompt, FinalIntelligence)
        
        # Post-process: Ensure title, description, and key metadata are populated/restored from base if AI skipped them
        if not result.title or result.title == "Unknown":
            result.title = base.title
        if not result.description or result.description == "Unknown":
            result.description = base.description
        if (not result.author_name or result.author_name == "Unknown") and base.author_name and base.author_name != "Unknown":
            result.author_name = base.author_name
        if (not result.company_name or result.company_name == "Unknown") and base.company_name and base.company_name != "Unknown":
            result.company_name = base.company_name
        if (not result.author_username or result.author_username == "Unknown") and base.author_username and base.author_username != "Unknown":
            result.author_username = base.author_username
        if (not result.platform or result.platform == "Unknown") and base.platform and base.platform != "Unknown":
            result.platform = base.platform
        if not result.topic or result.topic == "Unknown":
            result.topic = base.topic
        if not result.category or result.category == "Unknown":
            result.category = base.category
        if not result.sentiment or result.sentiment == "Unknown":
            result.sentiment = base.sentiment
            
        return result

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
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "groq/compound",
            "qwen/qwen3-32b",
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
                    logger.warning(f"Validation failed for {model_name}, attempting repair...")
                    try:
                        data = json.loads(clean_content)
                        
                        # 1. Flatten common wrapper keys
                        for wrapper in ["data", "author", "result", "extraction", "report"]:
                            if wrapper in data and isinstance(data[wrapper], dict):
                                data = data[wrapper]
                                break

                        # 2. Map non-standard keys
                        mapping = {
                            "name": "author_name",
                            "author": "author_name",
                            "handle": "author_username",
                            "username": "author_username",
                            "company": "company_name",
                        }
                        for old_key, new_key in mapping.items():
                            if old_key in data and new_key not in data:
                                data[new_key] = data[old_key]

                        # 3. Fix 'location' if it's a string
                        if "location" in data and isinstance(data["location"], str):
                            data["location"] = {"city": data["location"]}
                        
                        # 4. Fix 'followers' if it's a dict or string
                        if "followers" in data:
                            if isinstance(data["followers"], dict):
                                vals = [v for v in data["followers"].values() if isinstance(v, (int, float))]
                                data["followers"] = int(max(vals)) if vals else 0
                            elif isinstance(data["followers"], str):
                                try:
                                    data["followers"] = int(data["followers"].replace(",", "").replace("+", "").split()[0])
                                except:
                                    data["followers"] = 0
                        
                        # 5. Ensure social_profiles is a list of objects
                        if "social_profiles" in data and isinstance(data["social_profiles"], list):
                            new_profiles = []
                            for p in data["social_profiles"]:
                                if isinstance(p, str):
                                    new_profiles.append({"url": p, "platform": "Unknown"})
                                elif isinstance(p, dict) and "url" in p:
                                    new_profiles.append(p)
                            data["social_profiles"] = new_profiles

                        result = schema.model_validate(data)
                    except Exception as final_ve:
                        logger.error(f"Repair failed for {model_name}: {final_ve}")
                        continue

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
            result = schema(**data)
            
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
