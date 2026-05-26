import re
from playwright.sync_api import sync_playwright

def test_spys_one():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://spys.one/asia-proxy/")
        
        # Select 500 results
        try:
            with page.expect_navigation(timeout=30000):
                page.locator("select[name='xpp']").select_option("5")
        except: pass

        # Select SSL+
        # Find the select that contains "SSL+" option
        try:
            with page.expect_navigation(timeout=30000):
                page.locator("select").filter(has_text="SSL+").select_option(label="SSL+")
        except Exception as e:
            print(f"Could not select SSL+: {e}")

        # Extract IPs
        rows = page.query_selector_all("tr[class^='spy1x']")
        proxies = []
        for row in rows:
            ip_td = row.query_selector("td:nth-child(1) font")
            if ip_td:
                text = ip_td.inner_text().strip()
                match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})', text)
                if match:
                    proxies.append(match.group(1))

        print(f"Scraped {len(proxies)} proxies with SSL+ and 500 per page.")
        browser.close()

if __name__ == "__main__":
    test_spys_one()
