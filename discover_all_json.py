# File: discover_all_json.py

from playwright.sync_api import sync_playwright

DEALS_URL = "https://www.takealot.com/all-deals?sort=popularity"

def discover_all_json():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("[INFO] Listening for ALL JSON responses…")

        def handle_response(response):
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct.lower():
                    url = response.url
                    body = response.text()
                    snippet = body.replace("\n", " ")[:500]
                    print(f"\n[JSON] {url}\n{snippet}…\n")
            except Exception:
                pass

        page.on("response", handle_response)
        page.goto(DEALS_URL, timeout=60000)
        page.wait_for_timeout(15000)  # wait 15 seconds so all calls fire out
        browser.close()

if __name__ == "__main__":
    discover_all_json()

If __name__ --