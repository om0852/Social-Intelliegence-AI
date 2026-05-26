# ============================================================
# Proxy Scraper — Fetches free Indian proxies from public APIs
# ============================================================

import logging
import re
import requests
from typing import List, Dict

from bs4 import BeautifulSoup
from config import PROXY_SOURCES, TARGET_COUNTRY

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
                "country": TARGET_COUNTRY,
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
            protocols = item.get("protocols", [])
            proto = protocols[0] if protocols else "http"
            proxies.append({
                "ip": item.get("ip"),
                "port": int(item.get("port", 0)),
                "protocol": proto,
                "country": item.get("country", ""),
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
            # Accept all countries to hit 600+ proxies
            proxies.append({
                "ip": addr_match.group(1),
                "port": int(addr_match.group(2)),
                "protocol": protocol,
                "country": "ALL",
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
                "country": TARGET_COUNTRY,
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
        resp = requests.get("https://free-proxy-list.net/", timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        td_elements = soup.select('.fpl-list .table tbody tr td')
        
        for j in range(0, len(td_elements), 8):
            ip = td_elements[j].text.strip()
            port = td_elements[j + 1].text.strip()
            country = td_elements[j + 2].text.strip()
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



def scrape_all_sources() -> List[Dict]:
    """
    Master function: scrape all configured sources and return a
    deduplicated list of Indian proxy candidates.
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

    # Deduplicate by ip:port
    seen = set()
    unique: List[Dict] = []
    for proxy in all_proxies:
        key = f"{proxy['ip']}:{proxy['port']}"
        if key not in seen:
            seen.add(key)
            unique.append(proxy)

    logger.info(f"Total unique Indian proxy candidates: {len(unique)}")
    return unique
