
import csv
import json
import re

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
    if not value:
        return False

    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except ValueError:
        return False


def parse_price(value):
    value = (value or "").strip()

    if not value:
        return None

    value = value.replace("\u202f", "").replace(" ", "")
    value = value.replace("€", "").replace(",", ".")

    try:
        price = float(value)
        if price <= 0:
            return None
        return round(price, 2)
    except ValueError:
        return None


def make_id(name, merchant, url):
    base = f"{name}-{merchant}-{url}".lower()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    return base.strip("-")


def main():
    products = []
    seen = set()

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {CSV_FILE}"
        )

    with CSV_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file, delimiter=",")

        if not reader.fieldnames:
            raise ValueError(
                "Aucun en-tête trouvé dans product_feed.csv."
            )

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
            if not row:
                continue

            row = {
                (key or "").strip().lower():
                (value or "").strip()
                for key, value in row.items()
            }

            name = row.get("name", "")
            brand = row.get("brand", "")
            category = row.get("category", "")
            merchant = row.get("merchant", "")
            url = row.get("url", "")
            image = row.get("image", "")
            currency = row.get("currency", "").upper()

            if not name or not valid_url(url):
                continue

            price = parse_price(row.get("price", ""))

            if price is not None and currency != "EUR":
                continue

            if not currency:
                currency = "EUR"

            if image and not valid_url(image):
                image = ""

            product_id = row.get("id") or make_id(
                name,
                merchant,
                url
            )

            if product_id in seen:
                continue

            seen.add(product_id)

            products.append({
                "id": product_id,
                "name": name,
                "brand": brand,
                "category": category,
                "image": image,
                "merchant": merchant,
                "price": price,
                "currency": currency,
                "url": url,
                "checked_at": row.get("checked_at", "")
            })

    products.sort(
        key=lambda item: (
            item["name"].lower(),
            item["price"] is None,
            item["price"] or 0
        )
    )

    data = {
        "last_updated": datetime.now(
            timezone.utc
        ).isoformat(),
        "products": products
    }

    JSON_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    priced = sum(
        1 for product in products
        if product["price"] is not None
    )

    print(f"{len(products)} produits importés.")
    print(f"{priced} produits avec un prix.")
    print(f"{len(products) - priced} produits sans prix.")

    if not products:
        raise ValueError(
            "Aucun produit valide importé. "
            "Vérifie les noms et les liens HTTPS dans product_feed.csv."
        )


if __name__ == "__main__":
    main()
