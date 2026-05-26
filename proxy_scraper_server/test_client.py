import requests

try:
    print("Fetching a random proxy from the local server...")
    # 1. Ask your server for 1 working proxy
    proxy_data = requests.get("http://localhost:8500/proxy/random").json()
    
    if "error" in proxy_data:
        print(f"Error from server: {proxy_data['error']}")
    else:
        proxy_url = proxy_data["proxy_url"]
        print(f"Got proxy: {proxy_url}")

        # 2. Use it directly in your own request!
        proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        
        print("Making request to https://httpbin.org/ip using the proxy...")
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=15)
        print("Success! Target response:")
        print(response.json())

except Exception as e:
    print(f"Failed: {e}")
