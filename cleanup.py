# cleanup.py

import sqlite3
from datetime import datetime, timedelta

DB_PATH = "deals.db"

def clean_old_deals():
    """Remove deals older than 30 days to prevent database bloat."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    cursor.execute("DELETE FROM deals WHERE scraped_date < ?", (cutoff,))

    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    print(f"[INFO] Removed {deleted} old deals")

if __name__ == "__main__":
    clean_old_deals()
