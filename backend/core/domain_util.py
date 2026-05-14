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
        self.api_key = os.getenv("RAPIDAPI_KEY", "c3e134f96bmshbc2bd3b5c3f168ap13cd20jsn15d8c74b3370")
        self.host = "similarweb-insight-pro-api.p.rapidapi.com"

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
        """Fetches domain metrics from Similarweb via RapidAPI."""
        try:
            domain = urlparse(url).netloc
            if not domain:
                return None
            
            # Clean domain (remove www.)
            if domain.startswith("www."):
                domain = domain[4:]

            conn = http.client.HTTPSConnection(self.host)
            headers = {
                'x-rapidapi-key': self.api_key,
                'x-rapidapi-host': self.host,
                'Content-Type': "application/json"
            }

            logger.info(f"Fetching Similarweb metrics for: {domain}")
            conn.request("GET", f"/website/full?domain={domain}", headers=headers)

            res = conn.getresponse()
            raw_data = res.read().decode("utf-8")
            
            if res.status != 200:
                logger.error(f"Similarweb API error: {res.status} - {raw_data}")
                return None

            data = json.loads(raw_data)
            
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
            return metrics

        except Exception as e:
            logger.error(f"Failed to fetch domain metrics: {e}")
            return None

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
