import sqlite3
import pandas as pd
from datetime import datetime

# Connect to the SQLite database
conn = sqlite3.connect("deals.db")

# Get today's date in YYYY-MM-DD format
today = datetime.now().strftime("%Y-%m-%d")

# Query deals added today
query = """
SELECT title, price, orig_price, url, scraped_date
FROM deals
WHERE DATE(scraped_date) = ?
ORDER BY scraped_date DESC
"""
df = pd.read_sql_query(query, conn, params=(today,))

conn.close()

# Print or export results
if df.empty:
    print(f"No deals found for {today}.")
else:
    print(f"Deals found for {today}:\n")
    print(df.to_string(index=False))

    # Optional: save to CSV or HTML
    df.to_csv(f"deals_{today}.csv", index=False)
    df.to_html(f"deals_{today}.html", index=False)
    print(f"\nSaved to deals_{today}.csv and deals_{today}.html")
