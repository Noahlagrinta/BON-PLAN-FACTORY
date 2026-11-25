
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
    try:
        parsed = urlparse((value or "").strip())
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
        return round(price, 2) if price > 0 else None
    except ValueError:
        return None


def make_id(name, merchant, url):
    base = f"{name}-{merchant}-{url}".lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def main():
    if not CSV_FILE.exists():
        raise FileNotFoundError(f"Fichier introuvable : {CSV_FILE}")

    content = CSV_FILE.read_text(encoding="utf-8-sig").strip()

    if not content:
        raise ValueError("product_feed.csv est réellement vide.")

    first_line = content.splitlines()[0]

    if "," in first_line:
        delimiter = ","
    elif ";" in first_line:
        delimiter = ";"
    elif "\t" in first_line:
        delimiter = "\t"
    else:
        raise ValueError(
            f"Séparateur CSV introuvable. Première ligne : {first_line!r}"
        )

    reader = csv.DictReader(content.splitlines(), delimiter=delimiter)

    if not reader.fieldnames:
        raise ValueError(
            f"En-têtes introuvables. Première ligne : {first_line!r}"
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

    products = []
    seen = set()
    rejected = 0

    for row in reader:
        row = {
            (key or "").strip().lower(): (value or "").strip()
            for key, value in row.items()
        }

        name = row.get("name", "")
        merchant = row.get("merchant", "")
        url = row.get("url", "")

        if not name or not valid_url(url):
            rejected += 1
            continue

        currency = row.get("currency", "").upper() or "EUR"
        price = parse_price(row.get("price", ""))

        if price is not None and currency != "EUR":
            rejected += 1
            continue

        image = row.get("image", "")
        if image and not valid_url(image):
            image = ""

        product_id = row.get("id") or make_id(
            name, merchant, url
        )

        if product_id in seen:
            continue

        seen.add(product_id)

        products.append({
            "id": product_id,
            "name": name,
            "brand": row.get("brand", ""),
            "category": row.get("category", ""),
            "image": image,
            "merchant": merchant,
            "price": price,
            "currency": currency,
            "url": url,
            "checked_at": row.get("checked_at", "")
        })

    products.sort(key=lambda p: p["name"].lower())

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "products": products
    }

    JSON_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    priced = sum(p["price"] is not None for p in products)

    print(f"{len(products)} produits importés.")
    print(f"{priced} produits avec un prix.")
    print(f"{len(products) - priced} produits sans prix.")
    print(f"{rejected} lignes ignorées.")

    if not products:
        raise ValueError(
            "Aucun produit valide. Vérifie les noms et les liens HTTPS."
        )


if __name__ == "__main__":
    main()
