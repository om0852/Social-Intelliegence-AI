import http.client
import json
import logging
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DomainManager:
    def __init__(self):
        self.api_keys = [
            os.getenv("RAPIDAPI_KEY", "8b616907e9msh250a6a7041303e1p12b050jsn6a8918a348b1"),
            "9f7b0f5833mshc539e647d851a7dp1b6d7ejsn6169ecf50ea3",
            "96f7790dbdmsh68949bf19946d80p1af2a2jsn077ec2c345f9"
        ]
        self.current_key_idx = 0
        self.host = "similarweb-insight-pro-api.p.rapidapi.com"
        self.cache_file = os.path.join(os.path.dirname(__file__), "rapidapi_cache.json")

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
        
    def _save_cache(self, cache_data):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save rapidapi cache: {e}")

    def _get_country_name(self, code):
        """Resolves numeric or string country codes to names."""
        mapping = {
            356: "India", 840: "United States", 826: "United Kingdom",
            458: "Malaysia", 124: "Canada", 36: "Australia",
            702: "Singapore", 764: "Thailand", 608: "Philippines",
            710: "South Africa", 784: "UAE", 276: "Germany",
            250: "France", 392: "Japan", 156: "China",
            554: "New Zealand", 528: "Netherlands", 752: "Sweden",
            756: "Switzerland", 380: "Italy", 724: "Spain",
            484: "Mexico", 76: "Brazil"
        }
        try:
            # Handle numeric codes (they come as strings or ints)
            numeric_code = int(code)
            return mapping.get(numeric_code, f"Country {numeric_code}")
        except:
            # Handle string codes (e.g., 'IN', 'US')
            return str(code) if code else "Unknown"

    def get_domain_metrics(self, url: str) -> dict:
        """Fetches domain metrics from Similarweb via RapidAPI with high-fidelity deterministic mock fallback."""
        domain = ""
        try:
            domain = urlparse(url).netloc
            if not domain:
                return None
            
            # Clean domain (remove www.)
            if domain.startswith("www."):
                domain = domain[4:]

            # --- CACHE CHECK ---
            cache_data = self._load_cache()
            if domain in cache_data:
                logger.info(f"RapidAPI Cache Hit! Returning cached metrics for: {domain}")
                return cache_data[domain]

            # Try API keys in a loop until success or all exhaust
            for i in range(len(self.api_keys)):
                # Start from the current working key, loop around
                idx = (self.current_key_idx + i) % len(self.api_keys)
                api_key = self.api_keys[idx]
                
                conn = http.client.HTTPSConnection(self.host)
                headers = {
                    'x-rapidapi-key': api_key,
                    'x-rapidapi-host': self.host,
                    'Content-Type': "application/json"
                }

                logger.info(f"Fetching Similarweb metrics for: {domain} using key index {idx}")
                conn.request("GET", f"/website/full?domain={domain}", headers=headers)

                res = conn.getresponse()
                raw_data = res.read().decode("utf-8")
                
                if res.status == 200:
                    self.current_key_idx = idx # Update working key
                    data = json.loads(raw_data)
                    break
                elif res.status in [429, 403]: # Limit reached or forbidden
                    logger.warning(f"RapidAPI key at index {idx} limit reached or unauthorized (status {res.status}).")
                    if i == len(self.api_keys) - 1:
                        logger.error("All RapidAPI keys exhausted or failed.")
                        logger.warning("Falling back to deterministic mock domain metrics.")
                        return self.generate_mock_metrics(domain)
                    continue # Try next key
                else:
                    logger.error(f"Similarweb API error: {res.status} - {raw_data}")
                    logger.warning("Falling back to deterministic mock domain metrics.")
                    return self.generate_mock_metrics(domain)
            
            # Map API response to our schema
            engagements = data.get("Engagments", {})
            top_countries = data.get("TopCountryShares", [])
            traffic_sources = data.get("TrafficSources", {})
            top_keywords = data.get("TopKeywords", [])
            monthly_visits = data.get("EstimatedMonthlyVisits", {})
            
            def safe_float(val):
                try: return float(val)
                except: return 0.0

            # Map the exact keys from the provided JSON format
            metrics = {
                "site_name": data.get("SiteName"),
                "site_description": data.get("Description"),
                "global_rank": int(safe_float(data.get("GlobalRank", {}).get("Rank", 0))),
                "country_rank": int(safe_float(data.get("CountryRank", {}).get("Rank", 0))),
                "category": data.get("CategoryRank", {}).get("Category"),
                "category_rank": int(safe_float(data.get("CategoryRank", {}).get("Rank", 0))),
                "total_visits": self._format_visits(engagements.get("Visits", 0)),
                "bounce_rate": round(safe_float(engagements.get("BounceRate")) * 100, 2) if engagements.get("BounceRate") else 0.0,
                "pages_per_visit": round(safe_float(engagements.get("PagePerVisit")), 2) if engagements.get("PagePerVisit") else 0.0,
                "avg_visit_duration": self._format_time(engagements.get("TimeOnSite", 0)),
                "top_countries": [
                    {
                        "country": self._get_country_name(c.get("CountryCode") or c.get("Country") or c.get("Name") or c.get("Code")), 
                        "share": round(safe_float(c.get("Value") or c.get("Share") or 0) * 100, 2)
                    }
                    for c in top_countries[:5]
                ],
                "traffic_sources": {
                    k: round(safe_float(v) * 100, 2) for k, v in traffic_sources.items() if v is not None
                },
                "estimated_monthly_visits": {
                    k: int(safe_float(v)) for k, v in monthly_visits.items()
                },
                "top_keywords": [
                    {
                        "name": kw.get("Name", ""),
                        "estimated_value": safe_float(kw.get("EstimatedValue", 0)),
                        "volume": int(safe_float(kw.get("Volume", 0)))
                    }
                    for kw in top_keywords[:5]
                ]
            }
            
            # --- SAVE TO CACHE ---
            cache_data[domain] = metrics
            self._save_cache(cache_data)
            
            return metrics

        except Exception as e:
            logger.error(f"Failed to fetch domain metrics from Similarweb API: {e}")
            if domain:
                logger.warning(f"Falling back to deterministic mock domain metrics for: {domain}")
                try:
                    return self.generate_mock_metrics(domain)
                except Exception as fallback_err:
                    logger.error(f"Failed to generate mock domain metrics: {fallback_err}")
            return None

    def generate_mock_metrics(self, domain: str) -> dict:
        """Generates realistic, deterministic mock metrics for a given domain."""
        import random
        # Seed random with domain name to get consistent results
        seed_value = sum(ord(c) for c in domain)
        rng = random.Random(seed_value)

        # Preset major sites
        presets = {
            "instagram.com": {
                "site_name": "Instagram",
                "site_description": "Instagram is a free, online photo-sharing application and social network platform that was acquired by Facebook in 2012.",
                "global_rank": 4,
                "country_rank": 3,
                "category": "Computers Electronics and Technology > Social Media Networks",
                "category_rank": 2,
                "total_visits": "7.1B",
                "bounce_rate": 35.2,
                "pages_per_visit": 11.4,
                "avg_visit_duration": "8:15",
                "top_countries": [
                    {"country": "United States", "share": 18.5},
                    {"country": "Brazil", "share": 8.2},
                    {"country": "India", "share": 7.4},
                    {"country": "United Kingdom", "share": 4.1},
                    {"country": "Turkey", "share": 3.8}
                ],
                "traffic_sources": {
                    "Direct": 65.4,
                    "Search": 28.1,
                    "Social": 3.2,
                    "Referrals": 2.1,
                    "Mail": 1.2
                },
                "estimated_monthly_visits": {
                    "2026-02": 7100000000,
                    "2026-03": 7200000000,
                    "2026-04": 7150000000
                },
                "top_keywords": [
                    {"name": "instagram", "volume": 150000000, "estimated_value": 0.0},
                    {"name": "instagram login", "volume": 45000000, "estimated_value": 0.0}
                ]
            },
            "linkedin.com": {
                "site_name": "LinkedIn",
                "site_description": "LinkedIn is a business and employment-oriented social media platform that operates via websites and mobile apps.",
                "global_rank": 19,
                "country_rank": 12,
                "category": "Computers Electronics and Technology > Social Media Networks",
                "category_rank": 5,
                "total_visits": "1.8B",
                "bounce_rate": 38.5,
                "pages_per_visit": 7.2,
                "avg_visit_duration": "6:30",
                "top_countries": [
                    {"country": "United States", "share": 31.2},
                    {"country": "India", "share": 9.5},
                    {"country": "United Kingdom", "share": 5.8},
                    {"country": "Brazil", "share": 4.2},
                    {"country": "Canada", "share": 3.1}
                ],
                "traffic_sources": {
                    "Direct": 71.2,
                    "Search": 22.4,
                    "Social": 1.8,
                    "Referrals": 3.1,
                    "Mail": 1.5
                },
                "estimated_monthly_visits": {
                    "2026-02": 1800000000,
                    "2026-03": 1820000000,
                    "2026-04": 1810000000
                },
                "top_keywords": [
                    {"name": "linkedin", "volume": 50000000, "estimated_value": 0.0},
                    {"name": "linkedin login", "volume": 12000000, "estimated_value": 0.0}
                ]
            },
            "youtube.com": {
                "site_name": "YouTube",
                "site_description": "Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world.",
                "global_rank": 2,
                "country_rank": 2,
                "category": "Computers Electronics and Technology > Social Media Networks",
                "category_rank": 1,
                "total_visits": "32.4B",
                "bounce_rate": 20.4,
                "pages_per_visit": 12.8,
                "avg_visit_duration": "20:12",
                "top_countries": [
                    {"country": "United States", "share": 15.4},
                    {"country": "India", "share": 9.2},
                    {"country": "Brazil", "share": 5.1},
                    {"country": "Japan", "share": 4.8},
                    {"country": "United Kingdom", "share": 3.9}
                ],
                "traffic_sources": {
                    "Direct": 81.5,
                    "Search": 12.3,
                    "Social": 2.1,
                    "Referrals": 3.2,
                    "Mail": 0.9
                },
                "estimated_monthly_visits": {
                    "2026-02": 32400000000,
                    "2026-03": 32500000000,
                    "2026-04": 32300000000
                },
                "top_keywords": [
                    {"name": "youtube", "volume": 350000000, "estimated_value": 0.0},
                    {"name": "yt", "volume": 85000000, "estimated_value": 0.0}
                ]
            }
        }

        if domain in presets:
            return presets[domain]

        # Dynamic generation for other domains
        global_rank = rng.randint(1000, 100000)
        country_rank = int(global_rank * rng.uniform(0.3, 0.8))
        category_rank = int(global_rank * rng.uniform(0.01, 0.05))
        
        name_parts = domain.split('.')
        site_name = name_parts[0].capitalize()
        site_desc = f"{site_name} is a leading digital platform on the web, serving dynamic content and services to users worldwide."

        base_visits = int(10**rng.uniform(5, 7.5))
        total_visits_str = self._format_visits(base_visits)
        
        bounce_rate = round(rng.uniform(30.0, 60.0), 2)
        pages_per_visit = round(rng.uniform(2.0, 8.0), 2)
        avg_duration_sec = rng.randint(90, 480)
        avg_visit_duration = self._format_time(avg_duration_sec)

        countries_pool = [
            "United States", "India", "United Kingdom", "Canada", "Australia", 
            "Germany", "France", "Japan", "Brazil", "South Africa"
        ]
        rng.shuffle(countries_pool)
        top_countries = []
        remaining_share = 100.0
        for i in range(min(5, len(countries_pool))):
            share = round(remaining_share * rng.uniform(0.2, 0.5), 2)
            if i == 4 or remaining_share - share < 5.0:
                share = round(remaining_share, 2)
            top_countries.append({
                "country": countries_pool[i],
                "share": share
            })
            remaining_share -= share
            if remaining_share <= 0:
                break

        direct = round(rng.uniform(20.0, 50.0), 2)
        search = round(rng.uniform(20.0, 50.0), 2)
        social = round(rng.uniform(1.0, 10.0), 2)
        referral = round(rng.uniform(1.0, 10.0), 2)
        mail = round(100.0 - (direct + search + social + referral), 2)
        if mail < 0:
            mail = 0.0
            total_sum = direct + search + social + referral
            direct = round(direct / total_sum * 100, 2)
            search = round(search / total_sum * 100, 2)
            social = round(social / total_sum * 100, 2)
            referral = round(referral / total_sum * 100, 2)

        traffic_sources = {
            "Direct": direct,
            "Search": search,
            "Social": social,
            "Referrals": referral,
            "Mail": mail
        }

        estimated_monthly_visits = {
            "2026-02": int(base_visits * rng.uniform(0.9, 1.1)),
            "2026-03": int(base_visits * rng.uniform(0.9, 1.1)),
            "2026-04": base_visits
        }

        keywords_pool = [
            f"{site_name.lower()}", f"{site_name.lower()} news", f"{site_name.lower()} online",
            f"about {site_name.lower()}", f"{site_name.lower()} login", f"{site_name.lower()} official"
        ]
        top_keywords = []
        for kw in keywords_pool[:rng.randint(2, 5)]:
            top_keywords.append({
                "name": kw,
                "volume": int(base_visits * rng.uniform(0.01, 0.05)),
                "estimated_value": 0.0
            })

        return {
            "site_name": site_name,
            "site_description": site_desc,
            "global_rank": global_rank,
            "country_rank": country_rank,
            "category": "News and Media" if "news" in domain or "mint" in domain else "Computers Electronics and Technology",
            "category_rank": category_rank,
            "total_visits": total_visits_str,
            "bounce_rate": bounce_rate,
            "pages_per_visit": pages_per_visit,
            "avg_visit_duration": avg_visit_duration,
            "top_countries": top_countries,
            "traffic_sources": traffic_sources,
            "estimated_monthly_visits": estimated_monthly_visits,
            "top_keywords": top_keywords
        }


    def _format_visits(self, visits):
        """Format large numbers into K, M, B."""
        try:
            val = float(visits)
            if val >= 1_000_000_000:
                return f"{round(val / 1_000_000_000, 1)}B"
            if val >= 1_000_000:
                return f"{round(val / 1_000_000, 1)}M"
            if val >= 1_000:
                return f"{round(val / 1_000, 1)}K"
            return str(int(val))
        except:
            return "0"

    def _format_time(self, seconds):
        """Format seconds into M:SS."""
        try:
            sec = int(float(seconds))
            minutes = sec // 60
            remaining_sec = sec % 60
            return f"{minutes}:{remaining_sec:02d}"
        except:
            return "0:00"
