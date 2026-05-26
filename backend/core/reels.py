import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class ReelsService:
    def __init__(self):
        self.token = os.getenv("APIFY_TOKEN")
        self.api_url = f"https://api.apify.com/v2/acts/apify~instagram-reel-scraper/run-sync-get-dataset-items?token={self.token}"

    def get_reel_data(self, target_url: str) -> dict:
        """
        Runs the Apify Instagram Reel Scraper synchronously for a target Reel URL and returns mapped details.
        """
        logger.info(f"Triggering synchronous Apify scrape for Reel: {target_url}")
        
        payload = {
            "username": [target_url],
            "resultsLimit": 1
        }
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Apify Reel Scrape attempt {attempt}/{max_attempts}...")


                # Apify sync runs can take 30s to 3m. We set timeout to 240 seconds.
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=240
                )
                
                if response.status_code not in [200, 201]:
                    logger.error(f"Apify API returned error status {response.status_code}: {response.text}")
                    raise Exception(f"Apify API error (status {response.status_code}): {response.text}")
                    
                items = response.json()
                if not isinstance(items, list) or len(items) == 0:
                    raise Exception("No items returned from Instagram Reel Scraper. Verify the Reel URL is public and valid.")
                    
                reel = items[0]
                if isinstance(reel, dict) and ("error" in reel or "errorDescription" in reel):
                    error_msg = reel.get("errorDescription") or reel.get("error")
                    # If it's a restricted page block, warn and retry
                    if "restricted_page" in str(error_msg).lower() or "partial data" in str(error_msg).lower():
                        logger.warning(f"Attempt {attempt} hit restricted page block. Retrying...")
                        if attempt < max_attempts:
                            continue
                    raise Exception(f"Instagram Reel scraping failed: {error_msg}")
                
                # Map Apify's output to our standardized Social Intelligence schema
                return {
                    "success": True,
                    "data": {
                        "id": reel.get("id"),
                        "shortCode": reel.get("shortCode"),
                        "url": reel.get("url") or target_url,
                        "caption": reel.get("caption"),
                        "hashtags": reel.get("hashtags") or [],
                        "mentions": reel.get("mentions") or [],
                        "owner": reel.get("ownerUsername"),
                        "ownerFullName": reel.get("ownerFullName"),
                        "ownerId": reel.get("ownerId"),
                        "likes": reel.get("likesCount") or 0,
                        "views": reel.get("videoViewCount") or 0,
                        "plays": reel.get("videoPlayCount") or 0,
                        "commentsCount": reel.get("commentsCount") or 0,
                        "timestamp": reel.get("timestamp"),
                        "videoDuration": reel.get("videoDuration"),
                        "thumbnail": reel.get("displayUrl"),
                        "videoUrl": reel.get("videoUrl"),
                        "downloadedVideo": reel.get("downloadedVideo"),
                        "location": reel.get("locationName"),
                        "music": reel.get("musicInfo") or {},
                        "transcript": reel.get("transcript"),
                        "latestComments": reel.get("latestComments") or []
                    }
                }
                
            except requests.exceptions.Timeout:
                logger.error(f"Attempt {attempt} timed out.")
                if attempt == max_attempts:
                    raise Exception("Scraping execution timed out. Apify took too long to return data.")
            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {e}")
                if attempt == max_attempts:
                    raise Exception(str(e))
