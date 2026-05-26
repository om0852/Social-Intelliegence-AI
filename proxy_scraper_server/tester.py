# ============================================================
# Proxy Tester — Validates proxies asynchronously for speed
# ============================================================

import asyncio
import time
import logging
from typing import List, Dict

import aiohttp

from config import PROXY_TEST_URL, PROXY_TEST_TIMEOUT, MAX_CONCURRENT_TESTS

logger = logging.getLogger(__name__)


async def _test_single_proxy(
    proxy: Dict, session: aiohttp.ClientSession, semaphore: asyncio.Semaphore
) -> Dict | None:
    """
    Send a GET request through a single proxy to httpbin.org/ip.
    Returns the proxy dict (with latency added) if successful, else None.
    """
    protocol = proxy.get("protocol", "http")
    ip = proxy["ip"]
    port = proxy["port"]

    # Build the proxy URL for aiohttp
    if protocol in ("socks5", "socks4"):
        proxy_url = f"socks5://{ip}:{port}"
    else:
        proxy_url = f"http://{ip}:{port}"

    async with semaphore:
        try:
            start = time.monotonic()
            async with session.get(
                PROXY_TEST_URL,
                proxy=proxy_url,
                timeout=aiohttp.ClientTimeout(total=PROXY_TEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status == 200:
                    elapsed = round(time.monotonic() - start, 3)
                    body = await resp.json()
                    proxy["latency"] = elapsed
                    proxy["exit_ip"] = body.get("origin", ip)
                    proxy["alive"] = True
                    logger.debug(
                        f"  ✔ {ip}:{port} ({protocol}) — {elapsed}s — exit IP: {proxy['exit_ip']}"
                    )
                    return proxy
        except Exception:
            pass  # Dead proxy — silently skip
    return None


async def test_proxies(candidates: List[Dict]) -> List[Dict]:
    """
    Test a list of proxy candidates concurrently.
    Returns only the proxies that responded successfully, sorted by latency (fastest first).
    """
    if not candidates:
        logger.warning("No proxy candidates to test.")
        return []

    logger.info(f"Testing {len(candidates)} proxy candidates (max {MAX_CONCURRENT_TESTS} concurrent)...")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TESTS)

    # aiohttp-socks is required for SOCKS proxy support through aiohttp
    try:
        from aiohttp_socks import ProxyConnector  # noqa: F401
        # If available, we can use a per-request proxy via the connector
    except ImportError:
        logger.info("aiohttp-socks not installed — SOCKS5 proxies will be skipped during testing.")

    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TESTS, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [_test_single_proxy(p, session, semaphore) for p in candidates]
        results = await asyncio.gather(*tasks)

    alive = [r for r in results if r is not None]
    # Sort by latency — fastest first
    alive.sort(key=lambda p: p.get("latency", 999))

    logger.info(f"✅ {len(alive)} / {len(candidates)} proxies are alive and responding.")
    return alive
