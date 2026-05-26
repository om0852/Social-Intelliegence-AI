import asyncio
import sys
import os
import urllib.parse
from playwright.async_api import async_playwright

async def test():
    query = "Honda Bigwing PCMC Central LinkedIn"
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(search_url)
        content = await page.content()
        with open("test_raw.html", "w", encoding="utf-8") as f:
            f.write(content)
        await browser.close()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
asyncio.run(test())
