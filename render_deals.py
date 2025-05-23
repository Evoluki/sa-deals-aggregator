import sqlite3
import datetime

DB_PATH     = "deals.db"
OUTPUT_HTML = "index.html"

def load_today_deals_with_low_and_category():
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Fetch today's deals plus each product's historic minimum price
    cur.execute("""
    SELECT d.title,
           d.price,
           d.orig_price,
           d.url,
           d.image,
           d.price_value,
           d.category,
           m.min_price
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
    for title, price, orig, url, img, price_value, category, min_price in rows:
        is_new_low = (price_value == min_price)
        deals.append({
            "title": title,
            "price": price,
            "orig_price": orig,
            "url": url,
            "image": img,
            "category": category or "Uncategorized",
            "is_new_low": is_new_low
        })
        categories.add(category or "Uncategorized")

    return today, deals, sorted(categories)

def render_html(date, deals, categories):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Top Deals for {date}</title>
  <style>
    body {{ font-family: sans-serif; max-width: 900px; margin: auto; padding: 1rem; }}
  <!-- Subscriber Signup -->
  <div id="signup" style="margin-bottom: 1.5rem; padding: 1rem; background: #f5f5f5; border-radius: 5px;">
    <h2>📬 Get these deals by email</h2>
    <form id="signup-form">
      <input type="email" id="email" placeholder="you@example.com" required
             style="padding:0.5rem; width:60%;max-width:300px; margin-right:0.5rem;" />
      <button type="submit" style="padding:0.5rem 1rem;">Subscribe</button>
    </form>
    <p id="signup-msg" style="color:green; display:none;">Thanks! Check your inbox.</p>
  </div>
    h1 {{ text-align: center; }}
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
  <h1>Top Deals for {date}</h1>

  <!-- Filter UI -->
  <div id="filters">
"""
    # Build category checkboxes
    for cat in categories:
        html += f'    <label><input type="checkbox" value="{cat}" checked> {cat}</label> \n'
    html += "  </div>\n\n"

    # Build deals
    for d in deals:
        badge = ' <span class="badge">🎉 New Low!</span>' if d["is_new_low"] else ""
        html += f'  <div class="deal" data-category="{d["category"]}">\n'
        if d["image"]:
            html += f'    <img src="{d["image"]}" alt="">\n'
        html += f'    <div class="info">\n'
        html += f'      <a href="{d["url"]}" target="_blank"><h2>{d["title"]}{badge}</h2></a>\n'
        html += f'      <div class="category">{d["category"]}</div>\n'
        html += f'      <div><span class="price">{d["price"]}</span>'
        if d["orig_price"]:
            html += f'<span class="orig">{d["orig_price"]}</span>'
        html += "</div>\n"
        html += "    </div>\n  </div>\n\n"

    # Add filtering script
    html += """
  <script>
    const filters = document.querySelectorAll('#filters input[type="checkbox"]');
    filters.forEach(cb => {
      cb.addEventListener('change', () => {
        const cat = cb.value;
        document.querySelectorAll('.deal').forEach(card => {
          if (card.dataset.category === cat) {
            card.style.display = cb.checked ? '' : 'none';
          }
        });
      });
    });
  </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[✓] Generated {len(deals)} deals in {OUTPUT_HTML} with categories and filters")

if __name__ == "__main__":
    today, deals, categories = load_today_deals_with_low_and_category()
    render_html(today, deals, categories)

<script>
  document
    .getElementById("signup-form")
    .addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("email").value;
      const res = await fetch("/api/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });
      if (res.ok) {
        document.getElementById("signup-msg").style.display = "block";
      } else {
        alert("Signup failed. Try again.");
      }
    });
</script>
