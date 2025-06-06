# ── scraper_takealot.py ──

import sqlite3
import time
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DB_PATH = "deals.db"
RETAILER = "takealot"


def fetch_takealot_deals_dom():
    """
    Visit Takealot’s All Deals page, wait for <article data-ref="product-card">,
    scroll to load lazily‐loaded cards, then return a list of dicts for each deal.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        # 1. Go to the All Deals page
        page.goto("https://www.takealot.com/all-deals", timeout=60000)

        # 2. Wait for at least one product‐card (article[data-ref="product-card"]) to appear
        try:
            page.wait_for_selector("article[data-ref='product-card']", timeout=20000)
        except:
            # If it times out, sleep a bit in case content is very slow
            page.wait_for_timeout(8000)

        # 3. Scroll down in a loop to trigger lazy loading (if any)
        for _ in range(10):
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        # 4. Grab the full HTML
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    deals = []

    # Select each <article data-ref="product-card">
    cards = soup.select("article[data-ref='product-card']")

    for card in cards:
        # — Title: <h4 id="product-card-heading-XX" class="product-card-module_product-title_…">
        title_el = card.select_one("h4[id^='product-card-heading']")
        title = title_el.get_text(strip=True) if title_el else None

        # — Link: <a class="product-card-module_link-underlay_3sfaA" href="/…/PLIDxxxxx">
        link_el = card.select_one("a.product-card-module_link-underlay_3sfaA")
        href = link_el["href"] if (link_el and link_el.has_attr("href")) else None
        url = f"https://www.takealot.com{href}" if (href and href.startswith("/")) else href

        # — Image: <img class="product-card-image-module_product-image_3mJsJ" data-ref="product-image" src="…">
        img_el = card.select_one("img.product-card-image-module_product-image_3mJsJ")
        image = img_el["src"] if (img_el and img_el.has_attr("src")) else None

        # — Current price: <li data-ref="price"> → <span class="currency plus …">R 3,099</span>
        price_value = None
        price = None
        price_el = card.select_one("li[data-ref='price'] span.currency")
        if price_el:
            raw = price_el.get_text().replace("R", "").replace(" ", "").replace(",", "")
            try:
                price_value = int(raw)
                price = f"R {price_value:,}".replace(",", " ")
            except ValueError:
                pass

        # — Original list price: <li data-ref="list-price"> → <span class="currency plus …">R 3,499</span>
        orig_el = card.select_one("li[data-ref='list-price'] span.currency")
        orig_price = orig_el.get_text(strip=True) if orig_el else None

        # — Product ID: either data-product-id or last segment of href
        pid = card.get("data-product-id") or (href.split("/")[-1] if href else None)

        # Only append if we have a non-empty title and a valid integer price_value
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
    """
    Create (if missing) a SQLite 'deals' table with columns:
    (id, retailer, product_id, title, url, price, price_value, orig_price, category, image, scraped_date)
    """
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
    """
    Insert each deal into SQLite, ignoring duplicates for (retailer, product_id, scraped_date).
    Return how many new rows were inserted.
    """
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

