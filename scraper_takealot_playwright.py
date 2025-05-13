from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL = "https://www.takealot.com"
DEALS_URL = BASE_URL + "/all-deals?sort=popularity"

def fetch_takealot_deals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        print("[INFO] Loading page…")
        page.goto(DEALS_URL, timeout=60000)

        # Give JS time to render
        page.wait_for_timeout(7000)

        # Scroll to load lazy items
        print("[INFO] Scrolling to trigger lazy loading…")
        for _ in range(15):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)

        # Debug outputs
        page.screenshot(path="takealot_debug.png", full_page=True)
        html = page.content()
        with open("takealot_raw.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("[INFO] Saved takealot_debug.png and takealot_raw.html for inspection")

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        browser.close()

    deals = []
    # Select each product-article
    for art in soup.select("div.search-product.grid.deals article[data-ref='product-card']"):
        # Link & URL
        link_tag = art.select_one("a[class^='product-card-module_link-underlay']")
        href = link_tag.get("href") if link_tag else None
        url  = urljoin(BASE_URL, href) if href else None

        # Title
        title_tag = art.select_one("h4[id^='product-card-heading']")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Current price
        curr = art.select_one("li[data-ref='price'] span.currency")
        price = curr.get_text(strip=True) if curr else None

        # List/original price
        old  = art.select_one("li[data-ref='list-price'] span.currency")
        orig_price = old.get_text(strip=True) if old else None

        # Image
        img = art.select_one("img[data-ref='product-image']")
        img_url = img.get("src") if img else None

        deals.append({
            "title": title,
            "url": url,
            "price": price,
            "orig_price": orig_price,
            "image": img_url,
        })

    return deals

if __name__ == "__main__":
    deals = fetch_takealot_deals()
    print(f"\n[INFO] Extracted {len(deals)} deals\n")
    for d in deals[:10]:
        print(f"- {d['title']}")
        print(f"    Price: {d['price']}  (Was: {d['orig_price']})")
        print(f"    Link:  {d['url']}")
        print(f"    Image: {d['image']}\n")
