# discover_loot_api.py

from playwright.sync_api import sync_playwright

DEALS_URL = "https://www.loot.co.za/deals"

def discover_loot_api():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("[INFO] Listening for JSON responses…")

        def log_json(response):
            ct = response.headers.get("content-type", "")
            if "application/json" in ct:
                print(f"\n[JSON] {response.url}\n{response.text()[:500]}...\n")

        page.on("response", log_json)
        page.goto(DEALS_URL, timeout=60000)
        page.wait_for_timeout(10000)
        browser.close()

if __name__ == "__main__":
    discover_loot_api()
