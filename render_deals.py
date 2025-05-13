import sqlite3
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

DB_PATH   = "deals.db"
TEMPLATE_DIR = "templates"
OUTPUT_HTML  = "deals_today.html"

def load_today_deals():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT title, price, orig_price, url, image
        FROM deals
        WHERE scraped_date = ?
        ORDER BY scraped_date DESC
        LIMIT 20
    """, (today,))
    rows = cur.fetchall()
    conn.close()
    # Convert to list of dicts
    deals = [
        {"title": t, "price": p, "orig_price": o, "url": u, "image": i}
        for (t, p, o, u, i) in rows
    ]
    return today, deals

def render_html(date, deals):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("deals_template.html")
    html = template.render(date=date, deals=deals)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] Wrote {len(deals)} deals to {OUTPUT_HTML}")

if __name__ == "__main__":
    date, deals = load_today_deals()
    render_html(date, deals)
