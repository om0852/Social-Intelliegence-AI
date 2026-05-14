import asyncio
import sys
import logging
from core.scraper import Scraper
from core.intelligence import IntelligenceEngine
from core.search_util import SearchManager

# Windows-specific: Force ProactorEventLoop for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logger = logging.getLogger(__name__)

async def run_social_intelligence_pipeline(url: str) -> dict:
    """
    Main Orchestrator for Part 2 (Non-Login Platforms).
    """
    scraper = Scraper(headless=False)
    engine = IntelligenceEngine()

    try:
        # Phase 1: Initial Scrape
        logger.info(f"--- Phase 1: Scraping {url} ---")
        scraped = await scraper.scrape_url(url)
        if not scraped["success"]:
            return scraped

        # Phase 2: Initial AI Analysis
        logger.info("--- Phase 2: AI Content Analysis ---")
        base_data = await engine.analyze_initial(url, scraped["text"], scraped.get("profile_links", []))
        
        # Phase 3: Conditional Enrichment (Scrape Profile)
        enriched_text = ""
        profile_url = base_data.profile_url
        social_links = []
        
        # SEARCH FALLBACK: If no profile URL found on page, search the web
        searcher = SearchManager(headless=False)
        profile_data = None
        if (not profile_url or profile_url.lower() == "null") and base_data.author_name:
            logger.info("No profile URL found on page. Triggering Browser Search Fallback...")
            profile_data = await searcher.find_author_profile_url(
                base_data.author_name, 
                base_data.company_name or "",
                base_data.publisher or ""
            )
            if profile_data:
                profile_url = profile_data["url"]
                # Use snippet from search result as enriched text to avoid auth-blocked scraping
                enriched_text += f"\n--- BING SEARCH SNIPPET (MAIN PROFILE) ---\n"
                enriched_text += profile_data["snippet"]

        # Also search for other social platforms
        if base_data.author_name:
            logger.info(f"Searching for social media profiles for {base_data.author_name}...")
            # Smart context: Authors often work for the publisher, not the company the article is ABOUT
            search_context = f"{base_data.publisher or ''} {base_data.company_name or ''}".strip()
            social_profiles = await searcher.find_social_profiles(base_data.author_name, search_context)
            if social_profiles:
                logger.info(f"Found {len(social_profiles)} social profiles. Trimming to top 8 for AI stability.")
                # Sort by snippet length or relevance if possible, here we just take top 8
                social_profiles = social_profiles[:8]
                social_links = [s["url"] for s in social_profiles]
                # Aggregate all snippets for AI enrichment with CLEAR URL LABELS
                for profile in social_profiles:
                    enriched_text += f"\n--- DATA FOR URL: {profile['url']} ---\n"
                    enriched_text += profile["snippet"] + "\n"
                
                # Update base_data with discovered links
                base_data.social_profiles = list(set(base_data.social_profiles + social_links))

        # Only scrape if it's NOT a social platform (to avoid auth walls)
        is_social = any(x in (profile_url or "").lower() for x in ["linkedin.com", "instagram.com", "twitter.com", "x.com", "facebook.com"])
        
        if profile_url and not is_social:
            logger.info(f"--- Phase 3: Enriching from Profile {profile_url} ---")
            profile_scraped = await scraper.scrape_profile(profile_url)
            if profile_scraped["success"]:
                enriched_text += f"\n--- EXTERNAL PROFILE CONTENT ({profile_url}) ---\n"
                enriched_text += profile_scraped["text"]
        elif profile_url and is_social:
            logger.info(f"Skipping direct scrape of social profile {profile_url} to avoid auth wall. Using Bing snippets instead.")
        
        if social_links:
            enriched_text += f"\n--- ADDITIONAL SOCIAL LINKS ---\n"
            enriched_text += "\n".join(social_links)

        # Phase 4: Final Synthesis
        logger.info("--- Phase 4: Final Data Merging ---")
        final_report = await engine.finalize_data(base_data, enriched_text if enriched_text else None)

        # Phase 5: Domain Metrics (Similarweb)
        from core.domain_util import DomainManager
        logger.info(f"--- Phase 5: Fetching Domain Metrics for {url} ---")
        domain_mgr = DomainManager()
        domain_metrics = domain_mgr.get_domain_metrics(url)
        if domain_metrics:
            final_report.domain_metrics = domain_metrics

        return {
            "success": True,
            "data": final_report.model_dump()
        }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test run
    test_url = "https://www.bwlegalworld.com/article/in-conversation-with-navdeep-choudhary-clo-yum-brands-india-606113"
    result = asyncio.run(run_social_intelligence_pipeline(test_url))
    import json
    print(json.dumps(result, indent=2))
