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
    """Fetch deals from Takealot’s All Deals page, return a list of deal dicts."""
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

        # Try waiting for at least one product card. If timeout, proceed anyway.
        try:
            page.wait_for_selector("article[data-ref='product-card']", timeout=30000)
        except Exception:
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(5000)

        # Scroll down multiple times until no new content appears
        last_height = 0
        scroll_attempts = 0
        while scroll_attempts < 8:
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(2000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    deals = []
    cards = soup.select("article[data-ref='product-card']")
    print(f"[DEBUG] Found {len(cards)} candidate cards")

    for card in cards:
        try:
            # Product ID: from data-product-id attribute or fallback
            pid = card.get("data-product-id", "").strip()

            # Title
            title_el = card.select_one("h4.product-card-module_product-title_16xh8")
            title = title_el.get_text(strip=True) if title_el else None

            # URL
            link_el = card.select_one("a.product-card-module_link-underlay_3sfaA")
            href = link_el.get("href", "") if link_el else ""
            url = f"https://www.takealot.com{href}" if href.startswith("/") else href

            # Image
            img_el = card.select_one("img[data-ref='product-image']")
            image = img_el.get("src") if img_el else None

            # Current price
            price_value = None
            price_el = card.select_one("li[data-ref='price'] span.currency")
            if price_el:
                raw = price_el.get_text(strip=True).replace("R", "").replace(",", "").split()[0]
                try:
                    price_value = int(raw)
                    price = f"R {price_value:,}"
                except (ValueError, TypeError):
                    price_value = None
                    price = None
            else:
                price = None

            # Original / list price
            orig_el = card.select_one("li[data-ref='list-price'] span.currency")
            orig_price = orig_el.get_text(strip=True) if orig_el else None

            # Only keep valid deals
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
            print(f"[ERROR] Processing card failed: {e}")
            continue

    # If none found, dump HTML for debugging
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
            (retailer, product_id, title, url, price, price_value, orig_price, category, image, scraped_date)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
