import asyncio
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.core.search_util import SearchManager

async def test():
    searcher = SearchManager(headless=True)
    res = await searcher.find_social_profiles("Honda Bigwing PCMC Central", "Instagram bigwingpcmccentral")
    import json
    print("\nFINAL RESULTS:")
    print(json.dumps(res, indent=2))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
asyncio.run(test())
