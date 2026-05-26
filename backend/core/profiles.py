import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class InstagramProfileService:
    def __init__(self):
        self.token = os.getenv("APIFY_TOKEN")
        self.api_url = f"https://api.apify.com/v2/acts/apify~instagram-profile-scraper/run-sync-get-dataset-items?token={self.token}"

    def get_profile_data(self, username: str, max_posts: int = 5) -> dict:
        """
        Runs the Apify Instagram Profile Scraper synchronously for a target username and returns mapped details.
        """
        # Clean username if it has leading @
        username = username.strip()
        if username.startswith("@"):
            username = username[1:]
            
        logger.info(f"Triggering synchronous Apify scrape for Instagram Profile: {username}")
        
        payload = {
            "usernames": [username],
            "maxPosts": max_posts,
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Apify Profile Scrape attempt {attempt}/{max_attempts}...")
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
                    raise Exception(f"No items returned from Instagram Profile Scraper for username '{username}'. Verify the username is public and valid.")
                    
                profile = items[0]
                if isinstance(profile, dict) and ("error" in profile or "errorDescription" in profile):
                    error_msg = profile.get("errorDescription") or profile.get("error")
                    # If it's a restricted page block, warn and retry
                    if "restricted_page" in str(error_msg).lower() or "partial data" in str(error_msg).lower():
                        logger.warning(f"Attempt {attempt} hit restricted page block. Retrying with a new residential proxy...")
                        if attempt < max_attempts:
                            continue
                    raise Exception(f"Instagram Profile scraping failed: {error_msg}")
                
                # Map Apify's output to our standardized schema
                return {
                    "success": True,
                    "data": {
                        "id": profile.get("id"),
                        "username": profile.get("username") or username,
                        "url": profile.get("url") or f"https://www.instagram.com/{username}/",
                        "fullName": profile.get("fullName"),
                        "biography": profile.get("biography"),
                        "about": profile.get("about") or {},
                        "followersCount": profile.get("followersCount") or 0,
                        "followsCount": profile.get("followsCount") or 0,
                        "postsCount": profile.get("postsCount") or 0,
                        "highlightReelCount": profile.get("highlightReelCount") or 0,
                        "igtvVideoCount": profile.get("igtvVideoCount") or 0,
                        "isBusinessAccount": profile.get("isBusinessAccount") or False,
                        "joinedRecently": profile.get("joinedRecently") or False,
                        "hasChannel": profile.get("hasChannel") or False,
                        "businessCategoryName": profile.get("businessCategoryName"),
                        "private": profile.get("private") or False,
                        "verified": profile.get("verified") or False,
                        "externalUrl": profile.get("externalUrl"),
                        "externalUrls": profile.get("externalUrls") or [],
                        "profilePicUrl": profile.get("profilePicUrl"),
                        "profilePicUrlHD": profile.get("profilePicUrlHD"),
                        "relatedProfiles": profile.get("relatedProfiles") or [],
                        "latestPosts": profile.get("latestPosts") or []
                    }
                }
                
            except requests.exceptions.Timeout:
                logger.error(f"Attempt {attempt} timed out.")
                if attempt == max_attempts:
                    raise Exception("Scraping execution timed out. Apify took too long to return profile data.")
            except Exception as e:
                logger.error(f"Attempt {attempt} failed: {e}")
                if attempt == max_attempts:
                    raise Exception(str(e))
