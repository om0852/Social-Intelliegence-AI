import urllib.request
import json
import time
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

def get_outbound_ip():
    url = "https://ipapi.co/json/"
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            ip = data.get("ip")
            country = data.get("country") or "Unknown"
            org = data.get("org") or "Unknown"
            return f"{ip} [Country: {country} | Org: {org}]"
    except Exception as e:
        return f"Error ({e})"

def main():
    print(Fore.MAGENTA + Style.BRIGHT + "\n=== Running Rotating Proxy Verification Test ===")
    print(Fore.WHITE + "Connecting through local proxy at http://127.0.0.1:8080...")

    # Configure urllib to use our local HTTP proxy
    proxy_handler = urllib.request.ProxyHandler({
        'http': 'http://127.0.0.1:8080',
        'https': 'http://127.0.0.1:8080'
    })
    opener = urllib.request.build_opener(proxy_handler)
    urllib.request.install_opener(opener)

    num_test_requests = 10
    discovered_ips = []

    print(Fore.CYAN + f"\nTriggering {num_test_requests} sequential requests to verify IP rotation...\n")

    for i in range(num_test_requests):
        start_time = time.time()
        ip = get_outbound_ip()
        duration = time.time() - start_time
        
        discovered_ips.append(ip)
        
        # Display index and result with color highlighting
        status_color = Fore.GREEN if "Error" not in ip else Fore.RED
        print(f"Request {i+1:02d} | "
              f"Time: {duration:5.2f}s | "
              f"External IP: {status_color}{ip}")
        
        # Micro sleep to prevent thrashing
        time.sleep(0.5)

    # Calculate statistics
    successful_ips = [ip for ip in discovered_ips if "Error" not in ip]
    unique_ips = set(successful_ips)

    print(Fore.MAGENTA + Style.BRIGHT + "\n=== Verification Summary ===")
    print(Fore.WHITE + f"Total Requests: {num_test_requests}")
    print(Fore.WHITE + f"Successful Requests: {len(successful_ips)}")
    print(Fore.WHITE + f"Unique Exit IPs Discovered: {Fore.YELLOW}{len(unique_ips)}")
    
    if len(unique_ips) > 1:
        print(Fore.GREEN + Style.BRIGHT + "[SUCCESS] IP rotation and Round-Robin load balancing are working beautifully!")
    else:
        print(Fore.YELLOW + "[WARNING] Only 1 unique IP was found. Ensure all Tor instances are fully bootstrapped and active.")

if __name__ == "__main__":
    main()
