from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.orchestrator import run_social_intelligence_pipeline
from core.reels import ReelsService
from core.profiles import InstagramProfileService
import uvicorn
import logging
import asyncio
import sys
from fastapi.responses import FileResponse

# Windows-specific: Force ProactorEventLoop for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Social Intelligence AI Engine")

@app.get("/analytics", response_class=FileResponse)
async def get_analytics():
    return "analytics.html"

@app.get("/bulk_results.json", response_class=FileResponse)
async def get_bulk_results():
    return "bulk_results.json"

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    logger.info(f"Startup: Using event loop: {loop.__class__.__name__}")

class ExtractRequest(BaseModel):
    url: str

class ProfileRequest(BaseModel):
    username: str
    max_posts: int = 5

@app.get("/")
def read_root():
    return {"message": "Social Intelligence AI API is online."}

@app.post("/extract")
async def extract_intelligence(request: ExtractRequest):
    """
    Triggers the 4-Phase Social Intelligence Pipeline for a non-login URL.
    """
    logger.info(f"Received extraction request for: {request.url}")
    result = await run_social_intelligence_pipeline(request.url)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown pipeline error"))
    
    return result

@app.post("/extract-reel")
def extract_reel(request: ExtractRequest):
    """
    Triggers dynamic real-time Instagram Reels scraping via Apify sync execution,
    extracts the owner's username, enriches it with their complete Instagram Profile data,
    and fetches Similarweb domain metrics for the Reel URL.
    """
    logger.info(f"Received Reel extraction request for: {request.url}")
    try:
        reels_service = ReelsService()
        reel_result = reels_service.get_reel_data(request.url)
        
        if not reel_result.get("success"):
            return reel_result
            
        reel_data = reel_result.get("data", {})
        username = reel_data.get("owner")
        
        profile_data = None
        if username:
            logger.info(f"Reel owner username identified: {username}. Fetching Instagram Profile data...")
            try:
                profile_service = InstagramProfileService()
                profile_result = profile_service.get_profile_data(username, max_posts=5)
                if profile_result.get("success"):
                    profile_data = profile_result.get("data")
                    logger.info(f"Successfully enriched Reel with Profile data for: {username}")
                else:
                    logger.warning(f"Failed to fetch profile data for username '{username}': {profile_result.get('error')}")
            except Exception as pe:
                logger.error(f"Error fetching profile data for '{username}': {pe}")
                
        # Fetch other social profiles and Synthesize Data with AI
        ai_analysis = None
        other_social_profiles = []
        owner_full_name = reel_data.get("ownerFullName") or username
        if owner_full_name:
            logger.info(f"Searching for other social platforms and running AI synthesis for: {owner_full_name}")
            try:
                from core.search_util import SearchManager
                from core.intelligence import IntelligenceEngine, InitialExtraction
                import asyncio
                
                async def fetch_and_analyze():
                    # 1. Fetch other social profiles
                    searcher = SearchManager(headless=False)
                    profiles = await searcher.find_social_profiles(owner_full_name, company=f"Instagram {username}")
                    
                    # 2. Build Base Extraction and Enriched Text
                    caption = reel_data.get("caption") or ""
                    base_data = InitialExtraction(
                        title=caption[:100] + "..." if len(caption) > 100 else caption,
                        description=caption,
                        author_name=owner_full_name,
                        author_username=username,
                        publisher="Instagram",
                        platform="Instagram",
                        profile_url=f"https://instagram.com/{username}"
                    )
                    
                    enriched_parts = []
                    if profile_data:
                        bio = profile_data.get("biography", "")
                        followers = profile_data.get("followersCount", 0)
                        following = profile_data.get("followsCount", 0)
                        enriched_parts.append(f"--- INSTAGRAM PROFILE ---\nBio: {bio}\nFollowers: {followers}\nFollowing: {following}")
                    
                    for p in profiles:
                        enriched_parts.append(f"--- DATA FOR URL: {p['url']} ---\n{p['snippet']}")
                    
                    enriched_text = "\n\n".join(enriched_parts)
                    
                    # 3. Finalize Data with Grok
                    engine = IntelligenceEngine()
                    final_report = await engine.finalize_data(base_data, enriched_text)
                    return profiles, final_report

                # Run both the search and the AI synthesis in the event loop
                other_social_profiles, final_report = asyncio.run(fetch_and_analyze())
                if final_report:
                    ai_analysis = final_report.model_dump()
            except Exception as e:
                logger.error(f"Failed to fetch other social profiles or run AI analysis: {e}")
                
        # Fetch Similarweb Domain Metrics for the Reel's URL domain (i.e. instagram.com)
        domain_metrics = None
        try:
            from core.domain_util import DomainManager
            logger.info(f"Fetching Domain Metrics for Reel URL: {request.url}")
            domain_mgr = DomainManager()
            domain_metrics = domain_mgr.get_domain_metrics(request.url)
        except Exception as de:
            logger.error(f"Failed to fetch domain metrics for '{request.url}': {de}")
            
        # Clean up heavy and unnecessary data from the profile before returning
        if profile_data:
            profile_data.pop("relatedProfiles", None)
            profile_data.pop("latestPosts", None)

        # Inject the profile, domain metrics, social profiles, and ai analysis into the reel response
        reel_data["profile"] = profile_data
        reel_data["domain_metrics"] = domain_metrics
        reel_data["other_social_profiles"] = other_social_profiles
        reel_data["ai_analysis"] = ai_analysis
        
        return {
            "success": True,
            "data": reel_data
        }
    except Exception as e:
        logger.error(f"Reel extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-profile")
def extract_profile(request: ProfileRequest):
    """
    Triggers dynamic real-time Instagram Profile scraping via Apify sync execution.
    """
    logger.info(f"Received Profile extraction request for username: {request.username}")
    try:
        service = InstagramProfileService()
        result = service.get_profile_data(request.username, max_posts=request.max_posts)
        return result
    except Exception as e:
        logger.error(f"Profile extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, loop="asyncio")
