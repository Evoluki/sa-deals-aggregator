import sqlite3
import datetime

DB_PATH     = "deals.db"
OUTPUT_HTML = "index.html"

def load_today_deals_with_low():
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Fetch today's deals plus each product's historic minimum price_value
    cur.execute("""
    SELECT d.title,
           d.price,
           d.orig_price,
           d.url,
           d.image,
           d.price_value,
           m.min_price
    FROM deals AS d
    JOIN (
        SELECT product_id, MIN(price_value) AS min_price
        FROM deals
        WHERE price_value IS NOT NULL
        GROUP BY product_id
    ) AS m
      ON d.product_id = m.product_id
    WHERE d.scraped_date = ?
    ORDER BY d.price_value ASC
    """, (today,))

    rows = cur.fetchall()
    conn.close()

    # Convert to list of dicts
    deals = []
    for title, price, orig, url, img, price_value, min_price in rows:
        deals.append({
            "title": title,
            "price": price,
            "orig_price": orig,
            "url": url,
            "image": img,
            "is_new_low": (price_value == min_price)
        })
    return today, deals

def render_html(date, deals):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Today's Top Deals</title>
  <style>
    body {{ font-family: sans-serif; max-width: 800px; margin: auto; padding: 1rem; }}
    h1 {{ text-align: center; }}
    .deal {{ border-bottom: 1px solid #ddd; padding: 0.5rem 0; display: flex; align-items: center; }}
    .deal img {{ width: 100px; height: auto; margin-right: 1rem; }}
    .info {{ flex: 1; }}
    .price {{ font-weight: bold; color: green; }}
    .orig {{ text-decoration: line-through; color: #888; margin-left: 0.5rem; }}
    .badge {{ background: gold; color: #333; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; margin-left: 0.5rem; }}
  </style>
</head>
<body>
  <h1>Top Deals for {date}</h1>
"""

    if deals:
        for d in deals:
            badge = ' <span class="badge">🎉 New Low!</span>' if d["is_new_low"] else ""
            html += f"""
  <div class="deal">
    {'<img src="' + d['image'] + '" alt="">' if d['image'] else ''}
    <div class="info">
      <a href="{d['url']}" target="_blank"><h2>{d['title']}{badge}</h2></a>
      <div>
        <span class="price">{d['price']}</span>
        {'<span class="orig">' + d['orig_price'] + '</span>' if d['orig_price'] else ''}
      </div>
    </div>
  </div>
"""
    else:
        html += "  <p>No deals found for today.</p>\n"

    html += """
</body>
</html>"""
    # Write out
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[✓] Wrote {len(deals)} deals (with New Low flags) to {OUTPUT_HTML}")

if __name__ == "__main__":
    today, deals = load_today_deals_with_low()
    render_html(today, deals)

