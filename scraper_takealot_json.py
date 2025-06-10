# scraper_takealot_sqlite.py

import sqlite3
import time
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DB_PATH = "deals.db"
RETAILER = "takealot"
DEBUG_HTML_PATH = "takealot_debug.html"


def fetch_takealot_deals_dom():
    """Fetch current Takealot deals by parsing the All Deals page DOM."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--single-process",
                "--disable-gpu"
            ]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        page.goto("https://www.takealot.com/all-deals", timeout=120000)

        # Wait up to 30s for any <article data-product-id> to appear
        try:
            page.wait_for_selector("article[data-product-id]", timeout=30000)
        except Exception:
            # If the above times out, at least wait for DOMContentLoaded
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(5000)

        # Scroll multiple times to load all lazy-loaded content
        last_height = 0
        for _ in range(8):
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        html = page.content()
        browser.close()

    # Parse with BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    deals = []
    cards = soup.select("article[data-product-id]")
    print(f"[DEBUG] Found {len(cards)} candidate cards")

    for card in cards:
        try:
            # 1) Product ID
            pid = card.get("data-product-id", "").strip()

            # 2) Title
            title_el = card.select_one("h4.product-card-module_product-title_16xh8")
            title = title_el.get_text(strip=True) if title_el else None

            # 3) URL
            link_el = card.select_one("a.product-card-module_link-underlay_3sfaA")
            href = link_el.get("href", "") if link_el else ""
            url = f"https://www.takealot.com{href}" if href.startswith("/") else href

            # 4) Image
            img_el = card.select_one("img[data-ref='product-image']")
            image = img_el.get("src") if img_el else None

            # 5) Current price
            price_value = None
            price_el = card.select_one("li[data-ref='price'] span.currency")
            if price_el:
                # e.g. "R 3,099" → "3099"
                price_text = (
                    price_el.get_text(strip=True)
                    .replace("R", "")
                    .replace(",", "")
                    .split()[0]
                )
                try:
                    price_value = int(price_text)
                    price = f"R {price_value:,}"
                except (ValueError, TypeError):
                    price_value = None

            # 6) Original (list) price if present
            orig_el = card.select_one("li[data-ref='list-price'] span.currency")
            orig_price = orig_el.get_text(strip=True) if orig_el else None

            if title and price_value is not None:
                deals.append({
                    "product_id": pid,
                    "title": title,
                    "url": url,
                    "price": price,
                    "price_value": price_value,
                    "orig_price": orig_price,
                    "category": "Other",
                    "image": image
                })
        except Exception as e:
            print(f"[ERROR] Failed to parse one card: {e}")
            continue

    # If zero deals, write a debug HTML for inspection
    if len(deals) == 0:
        print("[WARNING] No deals found! Saving HTML for debugging...")
        with open(DEBUG_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html)

    print(f"[INFO] Successfully parsed {len(deals)} deals")
    return deals


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS deals (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      retailer TEXT,
      product_id TEXT,
      title TEXT,
      url TEXT,
      price TEXT,
      price_value INTEGER,
      orig_price TEXT,
      category TEXT,
      image TEXT,
      scraped_date TEXT,
      UNIQUE(retailer, product_id, scraped_date)
    );
    """)
    conn.commit()
    return conn


def save_takealot(deals, conn):
    today = date.today().isoformat()
    cur = conn.cursor()
    inserted = 0
    for d in deals:
        cur.execute("""
          INSERT OR IGNORE INTO deals
            (retailer,product_id,title,url,price,price_value,orig_price,category,image,scraped_date)
          VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            RETAILER,
            d["product_id"],
            d["title"],
            d["url"],
            d["price"],
            d["price_value"],
            d["orig_price"],
            d["category"],
            d["image"],
            today
        ))
        if cur.rowcount:
            inserted += 1
    conn.commit()
    return inserted


if __name__ == "__main__":
    print("[INFO] Initializing database…")
    conn = init_db()

    print("[INFO] Fetching deals from Takealot via DOM…")
    deals = fetch_takealot_deals_dom()
    print(f"[INFO] Retrieved {len(deals)} deals from Takealot")

    print("[INFO] Saving to database…")
    count = save_takealot(deals, conn)
    print(f"[INFO] Inserted {count} new deals (duplicates ignored)")

    conn.close()
