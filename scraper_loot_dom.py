import sqlite3
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DB_PATH = "deals.db"
RETAILER = "loot"


def fetch_loot_deals_dom():
    """Fetch current Loot deals by parsing the Deals page DOM using updated selectors."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.loot.co.za/deals", timeout=60000)
        page.wait_for_load_state('networkidle')
        # Ensure lazy content loads
        for _ in range(5):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)
        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, 'lxml')
    deals = []
    # Each product wrapper
    for wrapper in soup.select("div.FeaturedDealProductCardView_product__1A25E[itemtype='http://schema.org/Product']"):
        # Title
        title_el = wrapper.select_one(".FeaturedDealProductCardView_title__3N6jq[itemprop='name']")
        title = title_el.get_text(strip=True) if title_el else None

        # URL
        link_el = wrapper.select_one("a[itemprop='url']")
        href = link_el['href'] if link_el and link_el.has_attr('href') else None
        url = f"https://www.loot.co.za{href}" if href and href.startswith('/') else href

        # Image
        img_el = wrapper.select_one(".FeaturedDealProductCardView_productImage__25Wjy[itemprop='image']")
        image = img_el['src'] if img_el and img_el.has_attr('src') else None

        # Price (deal price)
        price_meta = wrapper.select_one(".FeaturedDealProductCardView_dealPrice__18VW0 meta[itemprop='price']")
        price_value = None
        price = None
        if price_meta and price_meta.has_attr('content'):
            try:
                price_value = int(price_meta['content'])
                price = f"R {price_value:,}".replace(",", " ")
            except ValueError:
                pass

        # Original list price
        orig_el = wrapper.select_one(".ListPrice .price, .FeaturedDealProductCardView_listPrice__2ys6c .price")
        orig_price = orig_el.get_text(strip=True) if orig_el else None

        # Product ID
        pid = href.rstrip('/').split('/')[-1] if href else (title or '')[:50]

        if title and price_value is not None:
            deals.append({
                'product_id': pid,
                'title': title,
                'url': url,
                'price': price,
                'price_value': price_value,
                'orig_price': orig_price,
                'category': 'Other',
                'image': image
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


def save_loot(deals, conn):
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
            d['product_id'],
            d['title'],
            d['url'],
            d['price'],
            d['price_value'],
            d['orig_price'],
            d['category'],
            d['image'],
            today
        ))
        if cur.rowcount:
            inserted += 1
    conn.commit()
    return inserted


if __name__ == '__main__':
    print("[INFO] Initializing DB…")
    conn = init_db()
    print("[INFO] Fetching Loot deals via DOM parsing…")
    deals = fetch_loot_deals_dom()
    print(f"[INFO] Retrieved {len(deals)} deals from {RETAILER}")
    print("[INFO] Saving to DB…")
    count = save_loot(deals, conn)
    print(f"[INFO] Inserted {count} new deals for {RETAILER}")
    conn.close()
