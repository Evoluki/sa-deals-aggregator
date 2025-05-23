# scraper_takealot_api_fallback.py

from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL  = "https://www.takealot.com"
DEALS_URL = BASE_URL + "/all-deals?sort=popularity"

def fetch_takealot_deals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))
        page = context.new_page()
        print("[INFO] Loading deals page…")
        page.goto(DEALS_URL, timeout=60000)
        page.wait_for_timeout(8000)

        print("[INFO] Scrolling…")
        for _ in range(12):
            page.mouse.wheel(0, 800)
            page.wait_for_timeout(400)

        html = page.content()
        page.screenshot(path="fallback_debug.png", full_page=True)
        with open("fallback_raw.html", "w", encoding="utf-8") as f:
            f.write(html)
        browser.close()

    print("[INFO] Parsed HTML / saved fallback_debug.png & fallback_raw.html")
    soup = BeautifulSoup(html, "lxml")

    deals = []
    # Grab every article with data-ref="product-card"
    for art in soup.select("article[data-ref='product-card']"):
        # URL
        link = art.select_one("a.product-card-module_link-underlay_3sfaA")
        href = link.get("href") if link else ""
        full_url = urljoin(BASE_URL, href)

        # Title
        title_tag = art.select_one("h4[id^='product-card-heading']")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Current price
        curr_li = art.select_one("li[data-ref='price'] span.currency")
        price = curr_li.get_text(strip=True) if curr_li else None

        # Original price
        old_li  = art.select_one("li[data-ref='list-price'] span.currency")
        orig   = old_li.get_text(strip=True) if old_li else None

        # Image
        img = art.select_one("img[data-ref='product-image']")
        img_url = img.get("src") if img else None

        deals.append({
            "title": title,
            "url": full_url,
            "price": price,
            "orig_price": orig,
            "image": img_url,
        })

    return deals

if __name__ == "__main__":
    results = fetch_takealot_deals()
    print(f"\n[INFO] Found {len(results)} deals\n")
    for d in results[:10]:
        print(f"- {d['title']}")
        print(f"    Price: {d['price']}  (Was: {d['orig_price']})")
        print(f"    Link:  {d['url']}")
        print(f"    Image: {d['image']}\n")
