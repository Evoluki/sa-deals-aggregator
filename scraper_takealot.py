import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.takealot.com"
DEALS_URL = BASE_URL + "/all-deals?sort=popularity"

def fetch_takealot_deals():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/113.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(DEALS_URL, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")

    deals = []

    # Loop through product cards
    for card in soup.select("div[data-component='product-card']"):
        # Get the link
        link_tag = card.select_one("a.product-card-module_link-underlay_3sfaA")
        if not link_tag:
            continue

        relative_url = link_tag.get("href")
        full_url = urljoin(BASE_URL, relative_url)

        # Try to extract title
        title_tag = card.select_one("div[data-component='product-card-title'] span")
        title = title_tag.get_text(strip=True) if title_tag else "No title found"

        # Extract current price
        price_tag = card.select_one("span[data-testid='current-price']")
        price = price_tag.get_text(strip=True) if price_tag else "N/A"

        # Extract old/original price (if available)
        orig_tag = card.select_one("span[data-testid='old-price']")
        orig_price = orig_tag.get_text(strip=True) if orig_tag else None

        # Optional: image URL
        img_tag = card.select_one("img")
        img_url = img_tag["src"] if img_tag else None

        deals.append({
            "title": title,
            "url": full_url,
            "price": price,
            "orig_price": orig_price,
            "image": img_url,
        })

    return deals
