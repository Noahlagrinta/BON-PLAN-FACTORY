
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
        sample = file.read(4096)
        file.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(file, dialect=dialect)

        if not reader.fieldnames:
            raise ValueError("Le fichier CSV est vide.")

        reader.fieldnames = [
            (name or "").strip().lower().lstrip("\ufeff")
            for name in reader.fieldnames
        ]

        missing = [
            column for column in REQUIRED_COLUMNS
            if column not in reader.fieldnames
        ]

        if missing:
            raise ValueError(
                f"Colonnes manquantes : {missing}. "
                f"Colonnes trouvées : {reader.fieldnames}"
            )

        for row in reader:
            row = {
                (key or "").strip().lower(): (value or "").strip()
                for key, value in row.items()
            }

            name = row.get("name", "")
            merchant = row.get("merchant", "")
            url = row.get("url", "")
            currency = row.get("currency", "").upper()

            try:
                price = float(row.get("price", "").replace(",", "."))
            except ValueError:
                continue

            if not name or not merchant or not valid_url(url):
                continue

            if price <= 0 or currency != "EUR":
                continue

            product_id = row.get("id") or f"{name.lower()}-{merchant.lower()}"

            if product_id in seen:
                continue

            seen.add(product_id)

            image = row.get("image", "")
            if image and not valid_url(image):
                image = ""

            products.append({
                "id": product_id,
                "name": name,
                "brand": row.get("brand", ""),
                "category": row.get("category", ""),
                "image": image,
                "merchant": merchant,
                "price": round(price, 2),
                "currency": "EUR",
                "url": url,
                "checked_at": row.get("checked_at", "")
            })

    products.sort(key=lambda item: (item["name"].lower(), item["price"]))

    JSON_FILE.write_text(
        json.dumps({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "products": products
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"{len(products)} produits importés.")

if __name__ == "__main__":
    main()
