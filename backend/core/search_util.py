from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import logging
import asyncio
import sys
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()
PROXY_URL = os.getenv("PROXY_URL")

# Windows-specific: Force ProactorEventLoop for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

logger = logging.getLogger(__name__)

class SearchManager:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.semaphore = asyncio.Semaphore(1) # Sequential searches to ensure full page loads

    async def find_author_profile_url(self, author_name: str, company: str = "", publisher: str = "") -> str:
        """
        Searches for the author profile using a real browser to bypass blocks.
        """
        if not author_name or author_name.lower() == "unknown":
            return None

        # Windows-specific: Playwright requires ProactorEventLoop for subprocesses.
        try:
            loop = asyncio.get_running_loop()
            loop_name = loop.__class__.__name__
            if sys.platform == 'win32' and 'Proactor' not in loop_name:
                logger.info(f"Non-Proactor loop detected ({loop_name}). Running browser search in a dedicated ProactorEventLoop thread.")
                return await asyncio.to_thread(self._find_author_profile_url_with_proactor, author_name, company, publisher)
        except RuntimeError:
            pass

        return await self._find_author_profile_url_internal(author_name, company, publisher)

    def _find_author_profile_url_with_proactor(self, author_name: str, company: str, publisher: str) -> str:
        """
        Sync wrapper to run the async search in a new ProactorEventLoop.
        """
        new_loop = asyncio.ProactorEventLoop()
        try:
            return new_loop.run_until_complete(self._find_author_profile_url_internal(author_name, company, publisher))
        finally:
            new_loop.close()

    async def find_social_profiles(self, author_name: str, company: str = "") -> list:
        """
        Searches for social media profiles (LinkedIn, Twitter, etc).
        """
        if not author_name or author_name.lower() == "unknown":
            return []

        try:
            loop = asyncio.get_running_loop()
            loop_name = loop.__class__.__name__
            if sys.platform == 'win32' and 'Proactor' not in loop_name:
                return await asyncio.to_thread(self._find_social_profiles_with_proactor, author_name, company)
        except RuntimeError:
            pass

        return await self._find_social_profiles_internal(author_name, company)

    def _find_social_profiles_with_proactor(self, author_name: str, company: str) -> list:
        new_loop = asyncio.ProactorEventLoop()
        try:
            return new_loop.run_until_complete(self._find_social_profiles_internal(author_name, company))
        finally:
            new_loop.close()

    def _get_browser_kwargs(self):
        kwargs = {"headless": self.headless}
        if PROXY_URL:
            # Apify proxy format: http://user:pass@host:port
            if "@" in PROXY_URL:
                try:
                    auth_part, server_part = PROXY_URL.split("@")
                    server = auth_part.split("//")[0] + "//" + server_part
                    user_pass = auth_part.split("//")[1]
                    username, password = user_pass.split(":")
                    kwargs["proxy"] = {
                        "server": server,
                        "username": username,
                        "password": password
                    }
                except:
                    kwargs["proxy"] = {"server": PROXY_URL}
            else:
                kwargs["proxy"] = {"server": PROXY_URL}
        return kwargs
    
    def _decode_bing_redirect(self, url: str) -> str:
        """
        Decodes a Bing redirect URL (ck/a) to get the final destination.
        """
        if "ck/a" not in url or "&u=" not in url:
            return url
            
        try:
            import base64
            parsed = urllib.parse.urlparse(url)
            u_param = urllib.parse.parse_qs(parsed.query).get('u', [None])[0]
            if u_param:
                # Bing's base64 is often prefixed with 'a1'
                b64_str = u_param[2:] if u_param.startswith('a1') else u_param
                # Add padding if needed
                b64_str += '=' * (4 - len(b64_str) % 4)
                decoded = base64.b64decode(b64_str).decode('utf-8', errors='ignore')
                if "http" in decoded:
                    return decoded
        except Exception as e:
            logger.debug(f"Bing redirect decode failed: {e}")
        return url

    async def _find_author_profile_url_internal(self, author_name: str, company: str, publisher: str) -> dict:
        """
        Search for author profile using Playwright exclusively.
        Returns a dict with url and snippet.
        """
        query = f'"{author_name}" {company} {publisher} LinkedIn'
        logger.info(f"Searching for author profile on Bing: {query}")
        return await self._playwright_search(query, ["linkedin.com/in/", "staff", "authors", "profile/"])

    async def _find_social_profiles_internal(self, author_name: str, company: str) -> list:
        """
        Search for multiple social profiles using Playwright tabs.
        """
        if not author_name or author_name.lower() == "unknown":
            return []

        async with async_playwright() as p:
            import random
            
            # Randomized viewport to mimic different devices
            viewports = [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1536, "height": 864}
            ]
            
            browser_kwargs = self._get_browser_kwargs()
            # Add slowMo to mimic human interaction speed
            browser_kwargs["slow_mo"] = random.randint(50, 150)
            
            browser = await p.chromium.launch(**browser_kwargs)
            
            # Use a more comprehensive context
            context = await browser.new_context(
                viewport=random.choice(viewports),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York"
            )
            
            # Prepare search tasks for different platforms following [author] [company] [platform] profile
            search_tasks = [
                self._search_on_page(context, f'{author_name} {company} LinkedIn profile', "linkedin.com/in/"),
                self._search_on_page(context, f'{author_name} {company} Instagram profile', "instagram.com/"),
                self._search_on_page(context, f'{author_name} {company} Twitter X profile', "twitter.com/"),
                self._search_on_page(context, f'{author_name} {company} Facebook profile', "facebook.com/"),
                self._search_on_page(context, f'{author_name} {company} YouTube profile', "youtube.com/@")
            ]
            
            # Run in parallel
            results = await asyncio.gather(*search_tasks)
            await browser.close()
            
            # Flatten and unique results
            all_profiles = []
            seen_urls = set()
            for sublist in results:
                for item in sublist:
                    if item["url"] not in seen_urls:
                        all_profiles.append(item)
                        seen_urls.add(item["url"])
            
            return all_profiles

    async def _search_on_page(self, context, query: str, keyword: str, use_google: bool = False) -> list:
        async with self.semaphore:
            page = await context.new_page()
            
            # Optimize: Block heavy resources to speed up slow proxy
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", lambda route: route.abort())
            
            await Stealth().apply_stealth_async(page)
            found = []
            try:
                # Try specific search first
                search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
                logger.info(f"Searching Bing (Specific): {search_url}")
                await page.goto(search_url, wait_until="load", timeout=90000)
                await asyncio.sleep(5)
                
                results = await self._extract_results_from_page(page)
                
                # Check for matches in initial results
                for item in results:
                    self._check_match(item, keyword, query, found)
                
                # If NO MATCHES found, try a broader search (Name + Platform only)
                if not found:
                    # TRULY BROAD: Just Author Name + Platform
                    # Query parts: "[author name] [orgs] [platform] profile"
                    parts = query.split()
                    # Author name is usually the first 2 parts (First Last)
                    name = f"{parts[0]} {parts[1]}" if len(parts) > 1 else parts[0]
                    platform_hint = parts[-2] if len(parts) > 2 else ""
                    broad_query = f"{name} {platform_hint} profile"
                    
                    search_url = f"https://www.bing.com/search?q={urllib.parse.quote(broad_query)}"
                    logger.info(f"No match in specific results. Trying Broad Search: {search_url}")
                    await page.goto(search_url, wait_until="load", timeout=60000)
                    await asyncio.sleep(5)
                    results = await self._extract_results_from_page(page)
                    for item in results:
                        self._check_match(item, keyword, broad_query, found)
                
                logger.info(f"Total matches found: {len(found)}")
            except Exception as e:
                logger.error(f"Search failed for {query}: {e}")
            finally:
                await page.close()
            return found

    def _check_match(self, item: dict, keyword: str, query: str, found_list: list) -> bool:
        """Helper to check if a result item matches the target keyword/author with high precision."""
        href = item['href'].lower()
        text = item['text'].lower()
        snippet = item['snippet'].lower()
        combined_text = text + " " + snippet
        
        # Determine platform
        platform = ""
        if "linkedin" in keyword or "linkedin" in href: platform = "linkedin"
        elif "twitter" in keyword or "twitter" in href or "x.com" in href: platform = "twitter"
        elif "instagram" in keyword or "instagram" in href: 
            platform = "instagram"
            # EXCLUDE Instagram posts, reels, stories
            if any(x in href for x in ["/p/", "/reels/", "/reel/", "/stories/"]):
                return False
        elif "facebook" in keyword or "facebook" in href: 
            platform = "facebook"
            # EXCLUDE Facebook posts, photos, groups
            if any(x in href for x in ["/posts/", "/photos/", "/groups/", "permalink.php"]):
                return False
        elif "youtube" in keyword or "youtube" in href: platform = "youtube"
        
        # PRECISE NAME MATCHING:
        # We want to see at least two parts of the author's name in the result
        # Filter out common search terms
        query_clean = query.lower().replace("profile", "").replace("linkedin", "").replace("twitter", "").replace("instagram", "").replace("facebook", "").replace("youtube", "").replace(" x ", "")
        name_parts = [p for p in query_clean.split() if len(p) > 2]
        
        # Count how many parts of the name are found in the result title/snippet/URL
        matches_count = 0
        for part in name_parts:
            if part in (href + " " + combined_text):
                matches_count += 1
        
        # A match is valid if:
        # 1. The keyword is in the URL (direct hit)
        # 2. OR we found at least 2 parts of the name AND the platform is correct
        is_match = False
        if keyword in href:
            is_match = True
        elif platform and matches_count >= min(2, len(name_parts)):
            is_match = True
        elif platform == "twitter" and ("twitter" in combined_text or " x " in combined_text) and matches_count >= 1:
            is_match = True
            
        # Avoid search engine internal links
        if is_match and any(x in href for x in ["bing.com/search", "google.com/search", "microsoft.com", "bing.com/images"]):
            is_match = False
        
        if is_match:
            final_url = self._decode_bing_redirect(item['href'])
            if not any(f["url"] == final_url for f in found_list):
                logger.info(f"MATCH FOUND: {final_url} (Score: {matches_count}/{len(name_parts)})")
                found_list.append({
                    "url": final_url,
                    "snippet": item['snippet']
                })
                return True
        return False

    async def _extract_results_from_page(self, page) -> list:
        """Helper to extract result blocks from a search page."""
        return await page.evaluate("""
            () => {
                const results = [];
                // Target Bing's main result containers
                const items = document.querySelectorAll('li.b_algo');
                
                items.forEach(item => {
                    const link = item.querySelector('h2 a');
                    if (link && link.href) {
                        results.push({
                            href: link.href,
                            text: link.innerText,
                            snippet: item.innerText // Capture everything in the result block
                        });
                    }
                });
                
                // Fallback to all links if no b_algo found (unlikely but safe)
                if (results.length === 0) {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => ({
                            href: a.href,
                            text: a.innerText,
                            snippet: a.parentElement ? a.parentElement.innerText : ""
                        }))
                        .filter(item => item.href && item.href.startsWith('http'));
                }
                return results;
            }
        """)

    async def _playwright_search(self, query: str, keywords: list) -> str:
        """Helper updated to use Bing for reliable single profile discovery."""
        async with async_playwright() as p:
            browser_kwargs = self._get_browser_kwargs()
            browser = await p.chromium.launch(**browser_kwargs)
            
            # Use a realistic context
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            
            # Block heavy resources
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", lambda route: route.abort())
            await Stealth().apply_stealth_async(page)
            
            try:
                search_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
                logger.info(f"Direct Search Bing: {search_url}")
                await page.goto(search_url, wait_until="load", timeout=60000)
                
                # Allow results to render
                await asyncio.sleep(5)
                
                # Use Smart Extraction logic for direct search too
                results = await page.evaluate("""
                    () => {
                        const results = [];
                        const items = document.querySelectorAll('li.b_algo');
                        items.forEach(item => {
                            const link = item.querySelector('h2 a');
                            if (link && link.href) {
                                results.push({
                                    href: link.href,
                                    text: link.innerText,
                                    snippet: item.innerText
                                });
                            }
                        });
                        return results;
                    }
                """)
                
                for item in results:
                    href = item['href']
                    text = item['text'].lower()
                    snippet = item['snippet'].lower()
                    
                    # Resolve redirect first to check against keywords
                    final_url = self._decode_bing_redirect(href)
                    
                    is_match = False
                    if any(k in final_url.lower() for k in keywords):
                        is_match = True
                    elif "linkedin" in query.lower() and "linkedin" in (text + " " + snippet).lower():
                        is_match = True
                        
                    # Avoid search engine internal links
                    if is_match and any(x in final_url.lower() for x in ["bing.com/search", "google.com/search", "microsoft.com"]):
                        is_match = False
                        
                    if is_match:
                        logger.info(f"Found Match in Direct Search: {final_url}")
                        await browser.close()
                        return {
                            "url": final_url,
                            "snippet": item['snippet']
                        }
            except Exception as e:
                logger.error(f"Direct Bing search failed: {e}")
            finally:
                await browser.close()
        return None
