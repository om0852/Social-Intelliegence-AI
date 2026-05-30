import requests
import re
from bs4 import BeautifulSoup

def test_proxynova():
    print("--- ProxyNova ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        r = requests.get("https://www.proxynova.com/proxy-server-list/country-in", headers=headers, timeout=10)
        # Using regex directly on the HTML to find the obfuscated IPs
        # document.write('1'+'0'+'3'+'.'+'2'+'0'+'9'+'.'+'8'+'8'+'.'+'7'+'5');
        matches = re.finditer(r"document\.write\('([^']+)'(?: \+ '([^']+)')*\)", r.text)
        for match in matches:
            print("Found script snippet:", match.group(0))
    except Exception as e:
        print(f"ProxyNova error: {e}")

if __name__ == '__main__':
    test_proxynova()
