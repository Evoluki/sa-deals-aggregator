# scraper_loot.py

import re
import sqlite3
from datetime import date
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL  = "https://www.loot.co.za"
DEALS_URL = BASE_URL + "/deals"
DB_PATH   = "deals.db"
RETAILER  = "loot"

def fetch_loot_deals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(DEALS_URL, timeout=60000)
        page.wait_for_timeout(7000)

        # Scroll to lazy‑load more products
        for _ in range(10):
            page.mouse.wheel(0, 800)
            page.wait_for_timeout(500)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    deals = []

    # Select each product card by the shared wrapper class
    for card in soup.select("div.productCardView, div.ProductCardView_product__38Cxm.productCardView"):
        # Link and product_id
        a = card.select_one("a[itemprop='url']")
        href = a.get("href") if a else None
        url  = urljoin(BASE_URL, href) if href else None

        # Title
        title_el = card.select_one("div.ProductCardView_title__1BLTt[itemprop='name']")
        title = title_el.get_text(strip=True) if title_el else None

        # Deal price (current)
        deal_el = card.select_one("div.ProductCardView_price__q5a0N span.price")
        deal_text = deal_el.get_text(strip=True) if deal_el else ""
        deal_value = None
        if deal_text:
            m = re.search(r"\d[\d,\s]*", deal_text)
            if m:
                deal_value = int(m.group(0).replace(" ", "").replace(",", ""))

        # List/original price
        orig_el = card.select_one("div.ProductCardView_listPriceValue__3ER2W span.price")
        orig_text = orig_el.get_text(strip=True) if orig_el else None

        # Image URL
        img = card.select_one("img[itemprop='image']")
        img_src = img.get("src") if img else None
        image = urljoin("https:", img_src) if img_src and img_src.startswith("//") else img_src

        # product_id: from meta[itemprop='productID'] or slug
        pid_el = card.select_one("meta[itemprop='productID']")
        product_id = pid_el.get("content") if pid_el else (href.rstrip("/").split("/")[-1] if href else None)

        if title and url and deal_value is not None:
            deals.append({
                "product_id": product_id,
                "title": title,
                "url": url,
                "price": deal_text,
                "price_value": deal_value,
                "orig_price": orig_text,
                "image": image,
            })

    return deals

def save_loot_deals(deals, conn):
    today = date.today().isoformat()
    cur = conn.cursor()
    inserted = 0
    for d in deals:
        cur.execute("""
            INSERT OR IGNORE INTO deals
              (retailer, product_id, title, url, price, price_value, orig_price, image, scraped_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            RETAILER,
            d["product_id"],
            d["title"],
            d["url"],
            d["price"],
            d["price_value"],
            d["orig_price"],
            d["image"],
            today
        ))
        if cur.rowcount:
            inserted += 1
    conn.commit()
    return inserted

if __name__ == "__main__":
    from scraper_takealot_sqlite import init_db

    print(f"[INFO] Initializing database for {RETAILER}…")
    conn = init_db()

    print(f"[INFO] Fetching {RETAILER} deals…")
    deals = fetch_loot_deals()
    print(f"[INFO] Retrieved {len(deals)} deals from {RETAILER}")

    print(f"[INFO] Saving to database…")
    new_count = save_loot_deals(deals, conn)
    print(f"[INFO] Inserted {new_count} new deals for {RETAILER}")

    conn.close()
    