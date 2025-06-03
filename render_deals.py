import sqlite3
from datetime import date
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DB_PATH = "deals.db"
OUTPUT_HTML = "index.html"
# Paste your Google Form iframe embed snippet below:
GOOGLE_FORM_IFRAME = '''<iframe src="https://docs.google.com/forms/d/e/1FAIpQLSdqneIvJvYtPr9EMt7u3k17G9N3Y7WOgQoPu1aeMa0rVc89Kw/viewform?embedded=true" width="640" height="382" frameborder="0" marginheight="0" marginwidth="0">Loading…</iframe>'''


def load_today_deals_with_low_and_category():
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT d.retailer,
               d.title,
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
    for retailer, title, price, orig, url, img, category, is_new_low in rows:
        cat = f"{retailer.capitalize()} • {category or 'Other'}"
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


def render_deals_page(date_str, deals, categories):
    # Start HTML
    html = []
    html.append("<!DOCTYPE html>")
    html.append("<html lang=\"en\"><head>")
    html.append("<meta charset=\"UTF-8\"><title>Top Deals for {}</title>".format(date_str))
    html.append("<style>")
    html.append("body { font-family: sans-serif; max-width: 900px; margin: auto; padding: 1rem; }")
    html.append("h1 { text-align: center; }")
    html.append("#signup { margin-bottom: 1.5rem; padding: 1rem; background: #f5f5f5; border-radius: 5px; }")
    html.append("#filters { margin-bottom: 1rem; }")
    html.append(".deal { border-bottom: 1px solid #ddd; padding: 0.75rem 0; display: flex; align-items: center; }")
    html.append(".deal img { width: 100px; height: auto; margin-right: 1rem; }")
    html.append(".info { flex: 1; }")
    html.append(".category { display: inline-block; background: #eef; color: #225; padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.8rem; margin-bottom: 0.5rem; }")
    html.append(".price { font-weight: bold; color: green; }")
    html.append(".orig { text-decoration: line-through; color: #888; margin-left: 0.5rem; }")
    html.append(".badge { background: gold; color: #333; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.8rem; margin-left: 0.5rem; }")
    html.append("</style></head><body>")

    # Signup form
    html.append("<div id=\"signup\"><h2>📬 Get these deals by email</h2>")
    html.append(GOOGLE_FORM_IFRAME)
    html.append("</div>")

    # Page title
    html.append(f"<h1>Top Deals for {date_str}</h1>")

    # Category Filters
    html.append("<div id=\"filters\">")
    for cat in categories:
        html.append(f"<label><input type=\"checkbox\" value=\"{cat}\" checked> {cat}</label>")
    html.append("</div>")

    # Render each deal card
    for d in deals:
        badge = '<span class="badge">🎉 New Low!</span>' if d['is_new_low'] else ''
        html.append(f"<div class=\"deal\" data-category=\"{d['category']}\">")
        if d['image']:
            html.append(f"<img src=\"{d['image']}\" alt=\"{d['title']}\" />")
        html.append("<div class=\"info\">")
        html.append(f"<a href=\"{d['url']}\" target=\"_blank\"><h2>{d['title']}{badge}</h2></a>")
        html.append(f"<div class=\"category\">{d['category']}</div>")
        line = f"<div><span class=\"price\">{d['price']}</span>"
        if d['orig_price']:
            line += f"<span class=\"orig\">{d['orig_price']}</span>"
        line += "</div>"
        html.append(line)
        html.append("</div></div>")

    # JavaScript for filtering
    html.append("<script>")
    html.append("document.querySelectorAll('#filters input[type=\"checkbox\"]').forEach(cb => {")
    html.append("  cb.addEventListener('change', () => {")
    html.append("    const cat = cb.value;")
    html.append("    document.querySelectorAll('.deal').forEach(card => {")
    html.append("      card.style.display = document.querySelector(`#filters input[value='${cat}']`).checked ? '' : 'none';")
    html.append("    });")
    html.append("  });")
    html.append("});")
    html.append("</script>")

    html.append("</body></html>")
    return "\n".join(html)


def render_deals():
    today, deals, categories = load_today_deals_with_low_and_category()

    # === DEBUG: print depth of deals loaded ===
    print(f"DEBUG: Loaded {len(deals)} total deals for {today}. Categories: {categories}")

    if len(deals) == 0:
        # If there are truly zero rows for today, we want CI to fail loudly rather than silently.
        raise RuntimeError(f"No deals found for {today}—render aborted.")

    content = render_deals_page(today, deals, categories)
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[✓] Generated {len(deals)} deals in {OUTPUT_HTML}")


if __name__ == '__main__':
    render_deals()


