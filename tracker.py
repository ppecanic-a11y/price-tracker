import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Ovdje unesi proizvode koje pratiš
PRODUCTS = [
    {
        "id": "sony-a6400",
        "name": "Sony Alpha a6400 Body",
        "url": "https://www.aviteh.hr/sony-alpha-a6400-body.html",
        "fallback_selector": ".price-now, .regular-price",
    }
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def extract_price_from_schema(soup):
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            items = data if isinstance(data, list) else [data]
            for item in items:
                offers = item.get("offers")
                if offers:
                    if isinstance(offers, list):
                        offers = offers[0]
                    price = offers.get("price")
                    if price:
                        return float(str(price).replace(",", "."))
        except Exception:
            continue
    return None


def extract_price_from_html(soup, selector):
    elem = soup.select_one(selector)
    if not elem:
        return None
    raw_text = elem.get_text()
    cleaned = (
        re.sub(r"[^\d,\.]", "", raw_text).replace(".", "").replace(",", ".")
    )
    match = re.search(r"\d+\.?\d*", cleaned)
    return float(match.group()) if match else None


def fetch_price(product):
    try:
        res = requests.get(product["url"], headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return None
        soup = BeautifulSoup(res.text, "html.parser")
        price = extract_price_from_schema(soup)
        if price is None and product.get("fallback_selector"):
            price = extract_price_from_html(soup, product["fallback_selector"])
        return price
    except Exception as e:
        print(f"Greška za {product['name']}: {e}")
        return None


def main():
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            db = json.load(f)
    except FileNotFoundError:
        db = {}

    today = datetime.now().strftime("%Y-%m-%d")

    for p in PRODUCTS:
        pid = p["id"]
        price = fetch_price(p)

        if pid not in db:
            db[pid] = {
                "name": p["name"],
                "url": p["url"],
                "initial_price": price,
                "current_price": price,
                "lowest_price": price,
                "history": [],
            }

        if price is not None:
            entry = db[pid]
            entry["current_price"] = price
            if entry["lowest_price"] is None or price < entry["lowest_price"]:
                entry["lowest_price"] = price

            if not entry["history"] or entry["history"][-1]["date"] != today:
                entry["history"].append({"date": today, "price": price})
            else:
                entry["history"][-1]["price"] = price

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
