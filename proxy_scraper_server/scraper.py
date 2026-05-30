# ============================================================
# Proxy Scraper — Fetches free Indian proxies from public APIs
# ============================================================

import logging
import re
import requests
from typing import List, Dict

from bs4 import BeautifulSoup
from config import PROXY_SOURCES, ALLOWED_COUNTRIES

logger = logging.getLogger(__name__)


def _parse_plain_text_proxies(text: str) -> List[str]:
    """
    Extract ip:port pairs from plain-text proxy lists.
    Matches patterns like 103.21.244.0:8080
    """
    pattern = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})")
    return pattern.findall(text)


def fetch_proxyscrape(url: str, protocol: str) -> List[Dict]:
    """Fetch proxies from ProxyScrape API (plain text, one ip:port per line)."""
    proxies = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        raw_list = _parse_plain_text_proxies(resp.text)
        for addr in raw_list:
            ip, port = addr.split(":")
            proxies.append({
                "ip": ip,
                "port": int(port),
                "protocol": protocol,
                "country": "UNKNOWN", # ProxyScrape text API doesn't provide country
                "source": "proxyscrape",
            })
        logger.info(f"[ProxyScrape/{protocol}] Fetched {len(proxies)} proxies")
    except Exception as e:
        logger.warning(f"[ProxyScrape/{protocol}] Failed to fetch: {e}")
    return proxies


def fetch_geonode(url: str) -> List[Dict]:
    """Fetch proxies from Geonode JSON API."""
    proxies = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", [])
        for item in items:
            country = item.get("country", "")
            if country not in ALLOWED_COUNTRIES:
                continue
            protocols = item.get("protocols", [])
            proto = protocols[0] if protocols else "http"
            proxies.append({
                "ip": item.get("ip"),
                "port": int(item.get("port", 0)),
                "protocol": proto,
                "country": country,
                "source": "geonode",
            })
        logger.info(f"[Geonode] Fetched {len(proxies)} proxies")
    except Exception as e:
        logger.warning(f"[Geonode] Failed to fetch: {e}")
    return proxies


def fetch_spys_me(url: str, protocol: str) -> List[Dict]:
    """Fetch proxies from spys.me plain text list (all countries)."""
    proxies = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) < 2:
                continue
            addr_match = re.match(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})", parts[0])
            if not addr_match:
                continue
            
            # spys.me usually has the country in parts[1], e.g. "US-N-S"
            country_code = parts[1].split('-')[0] if len(parts) > 1 else "UNKNOWN"
            if country_code not in ALLOWED_COUNTRIES:
                continue

            proxies.append({
                "ip": addr_match.group(1),
                "port": int(addr_match.group(2)),
                "protocol": protocol,
                "country": country_code,
                "source": "spys_me",
            })
        logger.info(f"[SpysMe/{protocol}] Fetched {len(proxies)} proxies")
    except Exception as e:
        logger.warning(f"[SpysMe/{protocol}] Failed to fetch: {e}")
    return proxies


def fetch_free_proxy_list(url: str) -> List[Dict]:
    """Fetch proxies from proxy-list.download (plain text, already filtered by country)."""
    proxies = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        raw_list = _parse_plain_text_proxies(resp.text)
        for addr in raw_list:
            ip, port = addr.split(":")
            proxies.append({
                "ip": ip,
                "port": int(port),
                "protocol": "http",
                "country": "UNKNOWN",
                "source": "free_proxy_list",
            })
        logger.info(f"[FreeProxyList] Fetched {len(proxies)} proxies")
    except Exception as e:
        logger.warning(f"[FreeProxyList] Failed to fetch: {e}")
    return proxies


def fetch_free_proxy_list_net() -> List[Dict]:
    """Fetch proxies from free-proxy-list.net using BeautifulSoup."""
    proxies = []
    try:
        resp = requests.get("https://free-proxy-list.net/en/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        td_elements = soup.select('.fpl-list .table tbody tr td')
        
        for j in range(0, len(td_elements), 8):
            ip = td_elements[j].text.strip()
            port = td_elements[j + 1].text.strip()
            country = td_elements[j + 2].text.strip()
            
            # They use 2-letter country code
            if country not in ALLOWED_COUNTRIES:
                continue

            proxies.append({
                "ip": ip,
                "port": int(port),
                "protocol": "http",
                "country": country,
                "source": "free_proxy_list_net",
            })
        logger.info(f"[FreeProxyList.net] Fetched {len(proxies)} proxies via BS4")
    except Exception as e:
        logger.warning(f"[FreeProxyList.net] Failed to fetch: {e}")
    return proxies


def fetch_roosterkid(url: str, protocol: str) -> List[Dict]:
    """Fetch proxies from Roosterkid GitHub list."""
    proxies = []
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            # Roosterkid usually has plain IPs, but we check if any allowed country code is in the line
            # If line doesn't contain a country code, we skip it
            found_country = None
            for c in ALLOWED_COUNTRIES:
                if c in line:
                    found_country = c
                    break
            
            if found_country:
                match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3}:\d+)", line)
                if match:
                    ip, port = match.group(1).split(":")
                    proxies.append({
                        "ip": ip,
                        "port": int(port),
                        "protocol": protocol,
                        "country": found_country,
                        "source": "roosterkid",
                    })
        logger.info(f"[Roosterkid/{protocol}] Fetched {len(proxies)} proxies")
    except Exception as e:
        logger.warning(f"[Roosterkid/{protocol}] Failed to fetch: {e}")
    return proxies


def scrape_all_sources() -> List[Dict]:
    """
    Master function: scrape all configured sources and return a
    deduplicated list of proxy candidates from famous countries.
    """
    all_proxies: List[Dict] = []

    # -- ProxyScrape --
    all_proxies.extend(
        fetch_proxyscrape(PROXY_SOURCES["proxyscrape_http"], "http")
    )
    all_proxies.extend(
        fetch_proxyscrape(PROXY_SOURCES["proxyscrape_socks5"], "socks5")
    )

    # -- Geonode --
    all_proxies.extend(fetch_geonode(PROXY_SOURCES["geonode"]))

    # -- spys.me --
    all_proxies.extend(
        fetch_spys_me(PROXY_SOURCES["spys_me_http"], "http")
    )
    all_proxies.extend(
        fetch_spys_me(PROXY_SOURCES["spys_me_socks"], "socks5")
    )

    # -- Free Proxy List --
    all_proxies.extend(
        fetch_free_proxy_list(PROXY_SOURCES["free_proxy_list"])
    )

    # -- FreeProxyList.net (BeautifulSoup) --
    all_proxies.extend(fetch_free_proxy_list_net())

    # -- Roosterkid (GitHub) --
    all_proxies.extend(fetch_roosterkid(PROXY_SOURCES["roosterkid_https"], "http"))
    all_proxies.extend(fetch_roosterkid(PROXY_SOURCES["roosterkid_socks4"], "socks4"))
    all_proxies.extend(fetch_roosterkid(PROXY_SOURCES["roosterkid_socks5"], "socks5"))

    # Deduplicate by ip:port
    seen = set()
    unique: List[Dict] = []
    for proxy in all_proxies:
        key = f"{proxy['ip']}:{proxy['port']}"
        if key not in seen:
            seen.add(key)
            unique.append(proxy)

    logger.info(f"Total unique global proxy candidates: {len(unique)}")
    return unique
