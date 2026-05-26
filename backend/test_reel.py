import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_reel_extraction():
    url = "https://www.instagram.com/reel/C8abD-45e/"
    print(f"Testing Instagram Reel Extraction Endpoint with URL: {url}")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/extract-reel",
            json={"url": url},
            timeout=240  # Apify sync execution can take up to 3 minutes
        )
        
        duration = time.time() - start_time
        print(f"Extraction finished in {duration:.2f} seconds.")
        
        if response.status_code == 200:
            print("SUCCESS!")
            result = response.json()
            # Print formatted results
            print(json.dumps(result, indent=2))
        else:
            print(f"FAILED! Status: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    test_reel_extraction()
