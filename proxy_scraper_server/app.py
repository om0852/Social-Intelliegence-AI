# ============================================================
# Proxy Scraper Server — FastAPI Application
# ============================================================
# A standalone server that:
#   1. Scrapes free Indian proxies from public APIs every 10 minutes.
#   2. Tests each proxy for liveness and speed.
#   3. Exposes REST endpoints to get random or all active proxies.
# ============================================================

import asyncio
import json
import random
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import (
    SERVER_HOST,
    SERVER_PORT,
    REFRESH_INTERVAL_SECONDS,
    ACTIVE_PROXIES_FILE,
)
from scraper import scrape_all_sources
from tester import test_proxies

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("proxy_server")

# ── In-memory proxy pool ───────────────────────────────────────
active_proxies: List[Dict] = []
pool_last_refreshed: str = "never"
pool_refresh_count: int = 0


def _save_to_disk(proxies: List[Dict]) -> None:
    """Persist current proxy list to JSON file so it survives restarts."""
    try:
        with open(ACTIVE_PROXIES_FILE, "w") as f:
            json.dump(proxies, f, indent=2)
        logger.info(f"Saved {len(proxies)} active proxies to disk.")
    except Exception as e:
        logger.warning(f"Could not save proxies to disk: {e}")


def _load_from_disk() -> List[Dict]:
    """Load previously saved proxies (used on startup)."""
    path = Path(ACTIVE_PROXIES_FILE)
    if path.exists():
        try:
            with open(path) as f:
                proxies = json.load(f)
            logger.info(f"Loaded {len(proxies)} proxies from disk cache.")
            return proxies
        except Exception as e:
            logger.warning(f"Could not load proxy cache: {e}")
    return []


async def refresh_proxy_pool() -> None:
    """Scrape → Test → Update the in-memory proxy pool."""
    global active_proxies, pool_last_refreshed, pool_refresh_count

    logger.info("=" * 60)
    logger.info("🔄 Starting proxy pool refresh cycle...")
    logger.info("=" * 60)

    start = time.monotonic()

    # Step 1: Scrape all sources (sync — fast HTTP calls)
    candidates = scrape_all_sources()
    if not candidates:
        logger.warning("No proxy candidates scraped. Keeping old pool.")
        return

    # Step 2: Test them asynchronously
    alive = await test_proxies(candidates)

    elapsed = round(time.monotonic() - start, 2)

    if alive:
        active_proxies = alive
        _save_to_disk(alive)
        pool_last_refreshed = datetime.now(timezone.utc).isoformat()
        pool_refresh_count += 1
        logger.info(
            f"✅ Pool refreshed in {elapsed}s — "
            f"{len(alive)} active Indian proxies ready."
        )
    else:
        logger.warning(
            f"⚠ No alive proxies found this cycle ({elapsed}s). "
            f"Keeping previous pool of {len(active_proxies)} proxies."
        )


async def _background_refresh_loop() -> None:
    """Run the refresh cycle in a loop every REFRESH_INTERVAL_SECONDS."""
    while True:
        try:
            await refresh_proxy_pool()
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)


# ── FastAPI Lifespan ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background proxy refresh on startup."""
    global active_proxies

    # Load cached proxies from disk if available
    active_proxies = _load_from_disk()

    # Launch the background refresh loop
    task = asyncio.create_task(_background_refresh_loop())
    logger.info(
        f"🚀 Proxy Scraper Server started on {SERVER_HOST}:{SERVER_PORT} — "
        f"refreshing every {REFRESH_INTERVAL_SECONDS}s"
    )
    yield

    # Cleanup on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Proxy Scraper Server stopped.")


# ── FastAPI App ────────────────────────────────────────────────
app = FastAPI(
    title="Indian Proxy Scraper Server",
    description=(
        "Automatically scrapes, tests, and serves free Indian proxy IPs "
        "from public proxy lists. Refreshes every 10 minutes."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ──────────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check + summary of the proxy pool."""
    return {
        "service": "Indian Proxy Scraper Server",
        "status": "running",
        "active_proxies": len(active_proxies),
        "last_refreshed": pool_last_refreshed,
        "refresh_count": pool_refresh_count,
        "refresh_interval_seconds": REFRESH_INTERVAL_SECONDS,
    }


@app.get("/proxies")
async def get_all_proxies():
    """Return the full list of currently active Indian proxies."""
    return {
        "count": len(active_proxies),
        "proxies": active_proxies,
    }


@app.get("/proxy/random")
async def get_random_proxy():
    """Return one random active Indian proxy (for round-robin use)."""
    if not active_proxies:
        return {"error": "No active proxies available. Pool may still be loading."}
    proxy = random.choice(active_proxies)
    return {
        "proxy": proxy,
        "proxy_url": (
            f"socks5://{proxy['ip']}:{proxy['port']}"
            if proxy.get("protocol") in ("socks5", "socks4")
            else f"http://{proxy['ip']}:{proxy['port']}"
        ),
    }


@app.get("/proxy/fastest")
async def get_fastest_proxy():
    """Return the fastest (lowest-latency) proxy."""
    if not active_proxies:
        return {"error": "No active proxies available. Pool may still be loading."}
    # List is already sorted by latency
    proxy = active_proxies[0]
    return {
        "proxy": proxy,
        "proxy_url": (
            f"socks5://{proxy['ip']}:{proxy['port']}"
            if proxy.get("protocol") in ("socks5", "socks4")
            else f"http://{proxy['ip']}:{proxy['port']}"
        ),
    }


@app.post("/refresh")
async def trigger_manual_refresh():
    """Manually trigger a proxy pool refresh (useful for testing)."""
    await refresh_proxy_pool()
    return {
        "message": "Proxy pool refreshed.",
        "active_proxies": len(active_proxies),
        "last_refreshed": pool_last_refreshed,
    }


# ── Proxy Forwarding Endpoint ─────────────────────────────────

from pydantic import BaseModel
from typing import Optional


class FetchRequest(BaseModel):
    """Request body for the /fetch proxy forwarding endpoint."""
    url: str                                    # Target URL to fetch
    method: str = "GET"                         # HTTP method: GET, POST, PUT, DELETE, etc.
    headers: Optional[Dict[str, str]] = None    # Custom headers to send
    body: Optional[Dict] = None                 # JSON body (for POST/PUT)
    timeout: int = 30                           # Request timeout in seconds
    max_retries: int = 3                        # How many times to retry on failure


@app.post("/fetch")
async def fetch_via_proxy(req: FetchRequest):
    """
    Forward any HTTP request through a random Indian proxy.

    Usage (Postman):
        POST http://localhost:8500/fetch
        Body (JSON):
        {
            "url": "https://httpbin.org/ip",
            "method": "GET"
        }

    The response will contain the target's response + which proxy IP was used.
    """
    if not active_proxies:
        return {"error": "No active proxies available. Pool may still be loading."}

    import requests as req_lib
    import asyncio

    # Pick up to max_retries random proxies
    num_proxies = min(req.max_retries, len(active_proxies))
    chosen_proxies = random.sample(active_proxies, num_proxies)

    def do_request(proxy_info):
        protocol = proxy_info.get("protocol", "http")
        ip = proxy_info["ip"]
        port = proxy_info["port"]

        if protocol in ("socks5", "socks4"):
            proxy_url = f"socks5://{ip}:{port}"
        else:
            proxy_url = f"http://{ip}:{port}"

        proxy_dict = {
            "http": proxy_url,
            "https": proxy_url,
        }

        logger.info(f"🌐 [Parallel Fetch] Forwarding {req.method} {req.url} via proxy {proxy_url}")

        response = req_lib.request(
            method=req.method.upper(),
            url=req.url,
            headers=req.headers or {},
            json=req.body if req.method.upper() in ("POST", "PUT", "PATCH") else None,
            proxies=proxy_dict,
            timeout=req.timeout,
            verify=False,
        )
        return response, proxy_url, ip, proxy_info.get("country", "IN")

    loop = asyncio.get_running_loop()
    tasks = [loop.run_in_executor(None, do_request, p) for p in chosen_proxies]
    
    errors = []

    # Wait for the first successful completion
    for f in asyncio.as_completed(tasks):
        try:
            response, proxy_url, ip, country = await f

            # Try to parse response as JSON, fallback to text
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text

            return {
                "success": True,
                "proxy_used": proxy_url,
                "proxy_ip": ip,
                "proxy_country": country,
                "status_code": response.status_code,
                "response_headers": dict(response.headers),
                "response": response_body,
            }
        except req_lib.exceptions.Timeout:
            errors.append("Timeout")
        except Exception as e:
            errors.append(str(e))

    # If all parallel tasks failed
    return {
        "success": False,
        "error": f"All {num_proxies} parallel proxy attempts failed.",
        "details": errors
    }



# ── Run with Uvicorn ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
    )
