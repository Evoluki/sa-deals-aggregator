import sqlite3
import datetime

DB_PATH = "deals.db"
OUTPUT_HTML = "index.html"
# Paste the full Google Forms iframe embed code below:
GOOGLE_FORM_IFRAME = '''<iframe src="https://docs.google.com/forms/d/e/1FAIpQLSdqneIvJvYtPr9EMt7u3k17G9N3Y7WOgQoPu1aeMa0rVc89Kw/viewform?embedded=true" width="640" height="382" frameborder="0" marginheight="0" marginwidth="0">Loading…</iframe>'''


def load_today_deals_with_low_and_category():
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT d.title,
               d.price,
               d.orig_price,
               d.url,
               d.image,
               d.category,
               CASE WHEN d.price_value = m.min_price THEN 1 ELSE 0 END AS is_new_low
        FROM deals AS d
        JOIN (
            SELECT retailer, product_id, MIN(price_value) AS min_price
            FROM deals
            WHERE price_value IS NOT NULL
            GROUP BY retailer, product_id
        ) AS m
          ON d.retailer = m.retailer
         AND d.product_id = m.product_id
        WHERE d.scraped_date = ?
        ORDER BY d.price_value ASC
    """, (today,))

    rows = cur.fetchall()
    conn.close()

    deals = []
    categories = set()
    for title, price, orig, url, img, category, is_new_low in rows:
        cat = category or "Other"
        deals.append({
            "title": title,
            "price": price,
            "orig_price": orig,
            "url": url,
            "image": img,
            "category": cat,
            "is_new_low": bool(is_new_low)
        })
        categories.add(cat)

    return today, deals, sorted(categories)


def render_html(date, deals, categories):
    # Build HTML parts
    head = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <title>Top Deals for {date}</title>
  <style>
    body {{ font-family: sans-serif; max-width: 900px; margin: auto; padding: 1rem; }}
    h1 {{ text-align: center; }}
    #signup {{ margin-bottom: 1.5rem; padding: 1rem; background: #f5f5f5; border-radius: 5px; }}
    #filters {{ margin-bottom: 1rem; }}
    .deal {{ border-bottom: 1px solid #ddd; padding: 0.75rem 0; display: flex; align-items: center; }}
    .deal img {{ width: 100px; height: auto; margin-right: 1rem; }}
    .info {{ flex: 1; }}
    .category {{
      display: inline-block;
      background: #eef;
      color: #225;
      padding: 0.2rem 0.5rem;
      border-radius: 3px;
      font-size: 0.8rem;
      margin-bottom: 0.5rem;
    }}
    .price {{ font-weight: bold; color: green; }}
    .orig {{ text-decoration: line-through; color: #888; margin-left: 0.5rem; }}
    .badge {{ background: gold; color: #333; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; margin-left: 0.5rem; }}
  </style>
</head>
<body>
"""

    signup_section = f"""
  <div id=\"signup\">
    <h2>📬 Get these deals by email</h2>
    {GOOGLE_FORM_IFRAME}
  </div>
  <h1>Top Deals for {date}</h1>
"""

    # Filters
    filter_html = "  <div id=\"filters\">\n"
    for cat in categories:
        filter_html += f"    <label><input type=\"checkbox\" value=\"{cat}\" checked> {cat}</label>\n"
    filter_html += "  </div>\n"

    # Deals list
    deals_html = ""
    for d in deals:
        badge = '<span class=\"badge\">🎉 New Low!</span>' if d["is_new_low"] else ''
        deals_html += f"  <div class=\"deal\" data-category=\"{d['category']}\">\n"
        if d['image']:
            deals_html += f"    <img src=\"{d['image']}\" alt=\"{d['title']}\">\n"
        deals_html += "    <div class=\"info\">\n"
        deals_html += f"      <a href=\"{d['url']}\" target=\"_blank\"><h2>{d['title']}{badge}</h2></a>\n"
        deals_html += f"      <div class=\"category\">{d['category']}</div>\n"
        deals_html += f"      <div><span class=\"price\">{d['price']}</span>"
        if d['orig_price']:
            deals_html += f"<span class=\"orig\">{d['orig_price']}</span>"
        deals_html += "</div>\n"
        deals_html += "    </div>\n  </div>\n"

    # Scripts
    scripts = """
  <script>
    // Filter by category
    document.querySelectorAll('#filters input[type="checkbox"]').forEach(cb => {
      cb.addEventListener('change', () => {
        document.querySelectorAll('.deal').forEach(card => {
          const cat = card.getAttribute('data-category');
          card.style.display = document.querySelector('#filters input[value="' + cat + '"]').checked ? '' : 'none';
        });
      });
    });
  </script>
</body>
</html>
"""

    # Combine and write
    final_html = head + signup_section + filter_html + deals_html + scripts
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"[✓] Generated {len(deals)} deals in {OUTPUT_HTML}")


if __name__ == '__main__':
    today, deals, categories = load_today_deals_with_low_and_category()
    render_html(today, deals, categories)
