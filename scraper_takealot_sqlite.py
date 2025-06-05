# scraper_takealot_sqlite.py

import sqlite3
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import os

DB_PATH = "deals.db"
RETAILER = "takealot"


def fetch_takealot_deals_dom():
    """
    Fetch current Takealot deals by parsing the /all-deals page.
    This version writes out the raw HTML to takealot_raw.html and prints debug info.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.goto("https://www.takealot.com/all-deals", timeout=60000)

        # Wait up to 20s for <article data-ref="product-card"> to appear, otherwise wait 8s total
        try:
            page.wait_for_selector("article[data-ref='product-card']", timeout=20000)
        except:
            page.wait_for_timeout(8000)

        # Scroll several times to load lazy‐loaded deals
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        html = page.content()

        # --- DEBUG: save raw HTML so we can inspect it in Actions (or locally) if needed
        try:
            with open("takealot_raw.html", "w", encoding="utf-8") as f:
                f.write(html)
        except Exception as e:
            print(f"[DEBUG] Failed to write takealot_raw.html: {e}")

        browser.close()

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("article[data-ref='product-card']")
    print(f"[DEBUG] Found {len(cards)} <article data-ref='product-card'> elements on Takealot all-deals")

    # If zero cards, print first few lines of raw HTML for inspection
    if len(cards) == 0:
        snippet = html[:300].replace("\n", " ").strip()
        print(f"[DEBUG] Raw HTML snippet (first 300 chars): {snippet!r}")

    deals = []
    for card in cards:
        # Title
        title_el = card.select_one("h4[id^='product-card-heading']")
        title = title_el.get_text(strip=True) if title_el else None

        # Link
        link_el = card.select_one("a.product-card-module_link-underlay_3sfaA")
        href = link_el["href"] if link_el and link_el.has_attr("href") else None
        url = f"https://www.takealot.com{href}" if href and href.startswith("/") else href

        # Image
        img_el = card.select_one("img[data-ref='product-image']")
        image = img_el["src"] if img_el and img_el.has_attr("src") else None

        # Current price
        price_value = None
        price = None
        price_el = card.select_one("li[data-ref='price'] span.currency")
        if price_el:
            price_text = price_el.get_text().replace("R", "").replace(" ", "")
            try:
                price_value = int(price_text)
                price = f"R {price_value:,}".replace(",", " ")
            except ValueError:
                pass

        # Original list price
        orig_el = card.select_one("li[data-ref='list-price'] span.currency")
        orig_price = orig_el.get_text(strip=True) if orig_el else None

        # Product ID
        pid = card.get("data-product-id") or (href.split("/")[-1] if href else (title or "")[:50])

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
