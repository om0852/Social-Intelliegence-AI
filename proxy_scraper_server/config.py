# ============================================================
# Proxy Scraper Server — Configuration
# ============================================================
# All constants and proxy source URLs live here.

import os

# --- Server Settings ---
SERVER_HOST = os.getenv("PROXY_SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("PROXY_SERVER_PORT", "8500"))

# --- Proxy Scraping Settings ---
# How often (in seconds) to refresh the proxy list
REFRESH_INTERVAL_SECONDS = int(os.getenv("PROXY_REFRESH_INTERVAL", "120"))  # 2 minutes

# Target country code for filtering
TARGET_COUNTRY = "IN"  # India

# Maximum time (in seconds) to wait when testing a single proxy
PROXY_TEST_TIMEOUT = int(os.getenv("PROXY_TEST_TIMEOUT", "8"))

# How many proxies to test concurrently
MAX_CONCURRENT_TESTS = int(os.getenv("MAX_CONCURRENT_TESTS", "50"))

# URL used to verify a proxy is alive and to detect the exit IP
PROXY_TEST_URL = "http://httpbin.org/ip"

# File to persist active proxies (so they survive restarts)
ACTIVE_PROXIES_FILE = os.path.join(os.path.dirname(__file__), "active_proxies.json")

# --- Free Proxy API Sources ---
# Each source returns proxies in a known format. We handle parsing per source.
PROXY_SOURCES = {
    # ProxyScrape — free API, supports country + protocol filters
    "proxyscrape_http": (
        "https://api.proxyscrape.com/v2/"
        "?request=displayproxies&protocol=http&timeout=10000"
        "&country=IN&ssl=all&anonymity=all"
    ),
    "proxyscrape_socks5": (
        "https://api.proxyscrape.com/v2/"
        "?request=displayproxies&protocol=socks5&timeout=10000"
        "&country=IN&ssl=all&anonymity=all"
    ),

    # Geonode — structured JSON API with country filter
    "geonode": (
        "https://proxylist.geonode.com/api/proxy-list"
        "?limit=200&page=1&sort_by=lastChecked&sort_type=desc"
        "&country=IN&filterUpTime=80&protocols=http%2Chttps%2Csocks5"
    ),

    # spys.me — plain text list (all countries, we filter client-side)
    "spys_me_http": "https://spys.me/proxy.txt",
    "spys_me_socks": "https://spys.me/socks.txt",

    # Free-Proxy-List (plain text)
    "free_proxy_list": (
        "https://www.proxy-list.download/api/v1/get"
        "?type=http&anon=anonymous&country=IN"
    ),

    # Roosterkid / OpenProxyList (GitHub)
    "roosterkid_https": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt",
    "roosterkid_socks4": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4.txt",
    "roosterkid_socks5": "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5.txt",
}
