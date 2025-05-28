# scraper_loot_playwright.py

import sqlite3
import re
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DB_PATH  = "deals.db"
RETAILER = "loot"

def fetch_loot_deals():
    """Use Playwright to load Loot/Makro daily deals and return list of dicts."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.loot.co.za/deals", timeout=60000)
        page.wait_for_timeout(8000)
        # Scroll to trigger lazy-load
        for _ in range(10):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)
        html = page.content()
        browser.close()
    soup = BeautifulSoup(html, "lxml")
    deals = []
    # Each product is under itemscope Product
    for card in soup.select("div[itemtype='http://schema.org/Product']"):
        # Title
        t = card.select_one(".ProductCardView_title__1BLTt")
        title = t.get_text(strip=True) if t else None

        # URL
        a = card.select_one("a[itemprop='url']")
        href = a["href"] if a else None
        url = ("https://www.loot.co.za" + href) if href and href.startswith("/") else href

        # Image
        img = card.select_one("img[itemprop='image']")
        image = img["src"] if img else None

        # Price & orig
        offer = card.select_one("span[itemprop='offers']")
        price_value = None
        price = None
        if offer:
            m = offer.select_one("meta[itemprop='price']")
            if m:
                price_value = int(m["content"])
                price = f"R {price_value:,}".replace(",", " ")
        list_p = card.select_one(".ProductCardView_listPriceValue__3ER2W .price")
        orig_price = list_p.get_text(strip=True) if list_p else None

        # Product ID (from href slug)
        pid = None
        if href:
            pid = href.rstrip("/").split("/")[-1]

        if title and price_value:
            deals.append({
                "product_id": pid,
                "title": title,
                "url": url,
                "price": price,
                "price_value": price_value,
                "orig_price": orig_price,
                "category": "Other",
                "image": image,
            })
    return deals

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # ensure same table exists
    cur.execute("""
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

def save_loot(deals, conn):
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
    print("[INFO] Initializing DB…")
    conn = init_db()
    print("[INFO] Fetching Loot deals…")
    loot_deals = fetch_loot_deals()
    print(f"[INFO] Retrieved {len(loot_deals)} deals from {RETAILER}")
    print("[INFO] Saving to DB…")
    count = save_loot(loot_deals, conn)
    print(f"[INFO] Inserted {count} new deals for {RETAILER}")
    conn.close()
