import re
from playwright.sync_api import sync_playwright

def scrape_spys_one():
    print("Launching Playwright to scrape spys.one/asia-proxy/ ...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # 1. Navigate directly to the Asia proxy list page
        print("Navigating to https://spys.one/asia-proxy/ ...")
        page.goto("https://spys.one/asia-proxy/", timeout=60000)
        
        # 2. Change the "Per page" dropdown to 500
        # The dropdown has name="xpp" and the value for 500 is '5'
        print("Selecting 500 results per page and waiting for reload...")
        try:
            # We use expect_navigation to wait for the page reload that happens automatically when the dropdown changes
            with page.expect_navigation(timeout=30000):
                page.locator("select[name='xpp']").select_option("5")
        except Exception as e:
            print(f"Warning: Could not change dropdown to 500: {e}")

        # 3. Extract the IPs from the table
        print("Extracting IP addresses...")
        rows = page.query_selector_all("tr[class^='spy1x']")
        
        proxies = []
        for row in rows:
            # First column contains IP:Port
            ip_td = row.query_selector("td:nth-child(1) font")
            if ip_td:
                text = ip_td.inner_text().strip()
                match = re.search(r'(\d{1,3}(?:\.\d{1,3}){3}:\d{2,5})', text)
                if match:
                    proxies.append(match.group(1))

        print(f"\n[SUCCESS] Successfully Scraped {len(proxies)} proxies from spys.one/asia-proxy/!\n")
        
        print("Here are the first 15 proxies:")
        for prx in proxies[:15]:
            print(f" - {prx}")
            
        print("\nClosing browser...")
        browser.close()

if __name__ == "__main__":
    scrape_spys_one()
