import os
import certifi

# Tell Python/urllib to use certifi's CA bundle
os.environ['SSL_CERT_FILE'] = certifi.where()

import os
import sqlite3
import datetime
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Content, From, To

# Load .env (for local testing)
load_dotenv()

DB_PATH = "deals.db"
SENDGRID_KEY = os.getenv("SENDGRID_API_KEY")

# Replace these with your verified sender/recipient
SENDER_EMAIL = "mbelemartin.tm@gmail.com"
RECIPIENT_EMAIL = "mbelemartin.tm@gmail.com"

def get_new_low_deals():
    today = datetime.date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    SELECT title, price, orig_price, url
      FROM deals AS d
      JOIN (
        SELECT product_id, MIN(price_value) AS min_price
        FROM deals
        WHERE price_value IS NOT NULL
        GROUP BY product_id
      ) AS m
    ON d.product_id = m.product_id
    WHERE d.scraped_date = ? AND d.price_value = m.min_price
    ORDER BY d.price_value ASC
    LIMIT 10
    """, (today,))
    rows = cur.fetchall()
    conn.close()
    return rows

def build_email_content(deals):
    if not deals:
        return "<p>No new low deals today.</p>"
    html = "<h2>Today's New Low Deals</h2><ul>"
    for title, price, orig, url in deals:
        html += (
            f"<li><a href='{url}'>{title}</a> — <strong>{price}</strong>"
            + (f" <del>{orig}</del>" if orig else "")
            + "</li>"
        )
    html += "</ul>"
    return html

def send_email(html_content):
    message = Mail(
        from_email=From(SENDER_EMAIL),
        to_emails=To(RECIPIENT_EMAIL),
        subject=f"New Low Deals for {datetime.date.today().isoformat()}",
        html_content=Content("text/html", html_content)
    )
    sg = SendGridAPIClient(SENDGRID_KEY)
    response = sg.send(message)
    print(f"[INFO] Email sent: status {response.status_code}")

if __name__ == "__main__":
    deals = get_new_low_deals()
    content = build_email_content(deals)
    send_email(content)

