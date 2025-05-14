import re
import sqlite3
from datetime import date
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from bs4 import BeautifulSoup

BASE_URL  = "https://www.takealot.com"
DEALS_URL = BASE_URL + "/all-deals?sort=popularity"
DB_PATH   = "deals.db"

def fetch_takealot_deals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ))
        page = ctx.new_page()
        page.goto(DEALS_URL, timeout=60000)
        page.wait_for_timeout(7000)
        for _ in range(15):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    deals = []
    for art in soup.select("article[data-ref='product-card']"):
        href = art.select_one("a[class^='product-card-module_link-underlay']").get("href", "")
        full_url = urljoin(BASE_URL, href)

        title = art.select_one("h4[id^='product-card-heading']").get_text(strip=True) or ""

        price = art.select_one("li[data-ref='price'] span.currency")
        price_text = price.get_text(strip=True) if price else ""

        # Parse numeric price
        price_value = None
        if price_text:
            m = re.search(r"\d[\d,]*", price_text.replace(" ", ""))
            if m:
                price_value = int(m.group(0).replace(",", ""))

        orig = art.select_one("li[data-ref='list-price'] span.currency")
        orig_price = orig.get_text(strip=True) if orig else None

        img = art.select_one("img[data-ref='product-image']")
        image = img.get("src") if img else None

        m2 = re.search(r"/PLID(\d+)", full_url)
        product_id = m2.group(1) if m2 else None

        deals.append({
            "product_id": product_id,
            "title": title,
            "url": full_url,
            "price": price_text,
            "price_value": price_value,
            "orig_price": orig_price,
            "image": image,
        })
    return deals

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Create table if missing
    cur.execute("""
    CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT,
        title TEXT,
        url TEXT,
        price TEXT,
        price_value INTEGER,
        orig_price TEXT,
        image TEXT,
        scraped_date TEXT,
        UNIQUE(product_id, scraped_date)
    );
    """)
    # Migrate: add price_value if absent
    cur.execute("PRAGMA table_info(deals);")
    cols = [row[1] for row in cur.fetchall()]
    if "price_value" not in cols:
        print("[INFO] Migrating DB: adding price_value column")
        cur.execute("ALTER TABLE deals ADD COLUMN price_value INTEGER;")
    conn.commit()
    return conn

def save_deals(deals, conn):
    today = date.today().isoformat()
    cur = conn.cursor()
    inserted = 0
    for d in deals:
        if not d["product_id"]:
            continue
        try:
            cur.execute("""
                INSERT OR IGNORE INTO deals 
                (product_id, title, url, price, price_value, orig_price, image, scraped_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
        except Exception as e:
            print(f"[ERROR] Could not insert {d['product_id']}: {e}")
    conn.commit()
    return inserted

if __name__ == "__main__":
    print("[INFO] Initializing database…")
    conn = init_db()

    print("[INFO] Fetching deals…")
    deals = fetch_takealot_deals()
    print(f"[INFO] Retrieved {len(deals)} deals from Takealot")

    print("[INFO] Saving to database…")
    new_count = save_deals(deals, conn)
    print(f"[INFO] Inserted {new_count} new deals (duplicates ignored)")

    conn.close()
