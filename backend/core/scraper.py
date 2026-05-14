import asyncio
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging

# Windows-specific: Force ProactorEventLoop for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
from dotenv import load_dotenv

load_dotenv()
PROXY_URL = os.getenv("PROXY_URL")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self, headless=False):
        self.headless = headless

    def _get_browser_kwargs(self):
        kwargs = {"headless": self.headless}
        # Disable proxy for main scraper to avoid slow residential proxy timeouts
        # if PROXY_URL:
        #     kwargs["proxy"] = {"server": PROXY_URL}
        return kwargs

    async def scrape_url(self, url: str) -> dict:
        """
        Generic scraper for news, blogs, and articles.
        Returns clean text and the page's HTML.
        """
        # Windows-specific: Playwright requires ProactorEventLoop for subprocesses.
        # If the current loop is a SelectorEventLoop, we must run this in a separate thread.
        try:
            loop = asyncio.get_running_loop()
            loop_name = loop.__class__.__name__
            if sys.platform == 'win32' and 'Proactor' not in loop_name:
                logger.info(f"Non-Proactor loop detected ({loop_name}). Running scraper in a dedicated ProactorEventLoop thread.")
                return await asyncio.to_thread(self._scrape_url_with_proactor, url)
        except RuntimeError:
            pass

        return await self._scrape_url_internal(url)

    def _scrape_url_with_proactor(self, url: str) -> dict:
        """
        Sync wrapper to run the async scraper in a new ProactorEventLoop.
        """
        new_loop = asyncio.ProactorEventLoop()
        try:
            return new_loop.run_until_complete(self._scrape_url_internal(url))
        finally:
            new_loop.close()

    async def _scrape_url_internal(self, url: str) -> dict:
        """
        The actual playwright logic.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(**self._get_browser_kwargs())
            # Use a realistic User-Agent
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()
            
            # Apply Stealth
            try:
                await Stealth().apply_stealth_async(page)
            except Exception as e:
                logger.error(f"Stealth failed: {e}")
            
            try:
                logger.info(f"Scraping URL: {url}")
                # Navigate and wait for DOM content (faster than networkidle)
                await page.goto(url, wait_until="domcontentloaded", timeout=90000)
                
                # Wait a small bit for JS to settle
                await asyncio.sleep(2)
                
                # Get the page content
                html = await page.content()
                text = await page.evaluate("() => document.body.innerText")
                title = await page.title()
                
                # Extract potential author/profile links
                links = await page.eval_on_selector_all("a", "elements => elements.map(e => ({text: e.innerText, href: e.href}))")
                profile_links = [l for l in links if any(x in l['text'].lower() or x in l['href'].lower() for x in ["author", "profile", "about", "staff", "writer", "user", "member", "u/"])]
                
                return {
                    "success": True,
                    "url": url,
                    "title": title,
                    "text": text,
                    "profile_links": profile_links[:20],
                    "html": html[:100000]
                }
                
            except Exception as e:
                logger.error(f"Scrape failed for {url}: {e}")
                return {"success": False, "error": str(e), "url": url}
            finally:
                await browser.close()

    async def scrape_profile(self, url: str) -> dict:
        """
        Targeted scraper for author profiles or company bios.
        """
        return await self.scrape_url(url)

# Simple test runner
if __name__ == "__main__":
    import json
    scraper = Scraper(headless=False)
    url = "https://www.bwlegalworld.com/article/in-conversation-with-navdeep-choudhary-clo-yum-brands-india-606113"
    result = asyncio.run(scraper.scrape_url(url))
    print(json.dumps(result, indent=2)[:500] + "...")
