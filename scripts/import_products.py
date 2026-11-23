
import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CSV_FILE = ROOT / "product_feed.csv"
JSON_FILE = ROOT / "product_feed.json"

REQUIRED_COLUMNS = [
    "id", "name", "brand", "category", "image",
    "merchant", "price", "currency", "url", "checked_at"
]

def valid_url(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)

def main():
    products = []
    seen = set()

    with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or not all(
            column in reader.fieldnames for column in REQUIRED_COLUMNS
        ):
            raise ValueError("Les colonnes de product_feed.csv sont incorrectes.")

        for row in reader:
            name = (row.get("name") or "").strip()
            merchant = (row.get("merchant") or "").strip()
            url = (row.get("url") or "").strip()
            currency = (row.get("currency") or "").strip().upper()

            try:
                price = float((row.get("price") or "").replace(",", "."))
            except ValueError:
                continue

            if not name or not merchant or not valid_url(url):
                continue

            if price <= 0 or currency != "EUR":
                continue

            product_id = (row.get("id") or "").strip()
            if not product_id:
                product_id = f"{name.lower()}-{merchant.lower()}"

            if product_id in seen:
                continue

            seen.add(product_id)

            image = (row.get("image") or "").strip()
            if image and not valid_url(image):
                image = ""

            products.append({
                "id": product_id,
                "name": name,
                "brand": (row.get("brand") or "").strip(),
                "category": (row.get("category") or "").strip(),
                "image": image,
                "merchant": merchant,
                "price": round(price, 2),
                "currency": "EUR",
                "url": url,
                "checked_at": (row.get("checked_at") or "").strip()
            })

    products.sort(key=lambda item: (item["name"].lower(), item["price"]))

    output = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "products": products
    }

    JSON_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"{len(products)} produits importés.")

if __name__ == "__main__":
    main()
