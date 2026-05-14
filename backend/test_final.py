import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_pipeline():
    url = "https://www.livemint.com/news/us-news/trump-promised-to-hold-30-000-migrants-in-73-mn-guantanamo-center-a-year-later-it-holds-only-six-detainees-report-11778690247596.html"
    print(f"Testing Pipeline with URL: {url}")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/extract",
            json={"url": url},
            timeout=120
        )
        
        duration = time.time() - start_time
        print(f"Pipeline finished in {duration:.2f} seconds.")
        
        if response.status_code == 200:
            print("SUCCESS!")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"FAILED! Status: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    test_pipeline()
