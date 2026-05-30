import requests
import re
from bs4 import BeautifulSoup

def test_proxynova():
    print("--- ProxyNova ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get("https://www.proxynova.com/proxy-server-list/country-in", headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.select('table#tbl_proxy_list tbody tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 1:
                ip_td = tds[0]
                port_td = tds[1]
                # proxynova uses document.write to hide IP
                script = ip_td.find('script')
                if script:
                    match = re.search(r"document\.write\('([^']+)'\)", script.text)
                    if match:
                        ip = match.group(1)
                        port = port_td.text.strip()
                        print(f"ProxyNova IP: {ip}:{port}")
    except Exception as e:
        print(f"ProxyNova error: {e}")

def test_roosterkid():
    print("--- Roosterkid ---")
    try:
        r = requests.get("https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS.txt", timeout=10)
        for line in r.text.splitlines():
            if 'IN' in line or '🇮🇳' in line:
                match = re.search(r"(\d+\.\d+\.\d+\.\d+:\d+)", line)
                if match:
                    print(f"Roosterkid IP: {match.group(1)}")
    except Exception as e:
        print(f"Roosterkid error: {e}")

def test_iproyal():
    print("--- IPRoyal ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get("https://iproyal.com/free-proxy-list/?entries=100", headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        # IPRoyal might block or have divs
        ips = re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', r.text)
        print(f"IPRoyal found {len(ips)} IPs in source code.")
        if len(ips) > 0:
            print(f"Samples: {ips[:5]}")
    except Exception as e:
        print(f"IPRoyal error: {e}")

if __name__ == '__main__':
    test_proxynova()
    test_roosterkid()
    test_iproyal()
