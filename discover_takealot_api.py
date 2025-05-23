from playwright.sync_api import sync_playwright
import json

DEALS_URL = "https://www.takealot.com/all-deals?sort=popularity"

def discover_api():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("[INFO] Listening for JSON responses…")
        
        def handle_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct:
                    url = response.url
                    text = response.text()
                    # Only print if it looks like deal data:
                    if "products" in text.lower() or "listPrice" in text:
                        print(f"\n[JSON RESPONSE] {url}\n{text[:500]}...\n")
            except Exception:
                pass
        
        page.on("response", handle_response)
        page.goto(DEALS_URL, timeout=60000)
        page.wait_for_timeout(10000)   # let everything load
        browser.close()

if __name__ == "__main__":
    discover_api()
