import json
import requests
import time
import os

PROXY_FILE = "active_proxies.json"
TEST_URL = "https://httpbin.org/get"

def main():
    if not os.path.exists(PROXY_FILE):
        print(f"Error: {PROXY_FILE} not found.")
        return

    with open(PROXY_FILE, "r") as f:
        proxies_data = json.load(f)

    print(f"Loaded {len(proxies_data)} proxies from {PROXY_FILE}")
    print(f"Testing connection to: {TEST_URL}\n")

    for p in proxies_data:
        ip = p['ip']
        port = p['port']
        protocol = p.get('protocol', 'http')
        proxy_url = f"{protocol}://{ip}:{port}"
        
        proxies_dict = {
            "http": proxy_url,
            "https": proxy_url
        }

        print(f"Testing Proxy: {proxy_url} ... ", end="", flush=True)
        start_time = time.time()

        try:
            # We use a 10s timeout to avoid hanging too long on dead proxies
            response = requests.get(TEST_URL, proxies=proxies_dict, timeout=10)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"SUCCESS (Took {elapsed:.2f}s) - Status: {response.status_code}")
            else:
                print(f"FAILED - Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            # Proxies often fail (timeout, connection refused, etc.)
            print(f"FAILED - Error: {type(e).__name__}")

if __name__ == "__main__":
    main()
