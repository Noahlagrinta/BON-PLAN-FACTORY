
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
    "id",
    "name",
    "brand",
    "category",
    "image",
    "merchant",
    "price",
    "currency",
    "url",
    "checked_at",
]

OPTIONAL_COLUMNS = [
    "description",
    "old_price",
    "price_verified",
]


def clean(value):
    return str(value or "").strip()


def valid_url(value):
    value = clean(value)

    if not value:
        return ""

    try:
        parsed = urlparse(value)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            return value
    except Exception:
        pass

    return ""


def clean_price(value):
    value = clean(value)

    if not value:
        return ""

    value = value.replace(",", ".")
    value = re.sub(r"[^0-9.]", "", value)

    try:
        number = float(value)

        if number <= 0:
            return ""

        return str(number)
    except ValueError:
        return ""


def detect_delimiter(sample):
    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t"
        )
        return dialect.delimiter
    except csv.Error:
        return ","


def read_csv():
    if not CSV_FILE.exists():
        raise FileNotFoundError(
            "Le fichier product_feed.csv est introuvable."
        )

    content = CSV_FILE.read_text(
        encoding="utf-8-sig"
    )

    if not content.strip():
        raise ValueError(
            "Le fichier product_feed.csv est vide."
        )

    delimiter = detect_delimiter(content[:5000])

    reader = csv.DictReader(
        content.splitlines(),
        delimiter=delimiter
    )

    if not reader.fieldnames:
        raise ValueError(
            "Aucun en-tête trouvé dans product_feed.csv."
        )

    headers = [
        clean(header).lower()
        for header in reader.fieldnames
    ]

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in headers
    ]

    if missing:
        raise ValueError(
            "Colonnes obligatoires manquantes : "
            + ", ".join(missing)
        )

    reader.fieldnames = headers

    return list(reader)


def convert_product(row):
    product = {
        "id": clean(row.get("id")),
        "name": clean(row.get("name")),
        "brand": clean(row.get("brand")),
        "category": clean(row.get("category")) or "Autres",
        "image": valid_url(row.get("image")),
        "merchant": clean(row.get("merchant")),
        "price": clean_price(row.get("price")),
        "currency": clean(row.get("currency")) or "€",
        "url": valid_url(row.get("url")),
        "checked_at": clean(row.get("checked_at")),
        "description": clean(row.get("description")),
        "old_price": clean_price(row.get("old_price")),
        "price_verified": (
            clean(row.get("price_verified")).lower()
            in ("true", "1", "oui", "yes")
        ),
    }

    if not product["checked_at"]:
        product["checked_at"] = datetime.now(
            timezone.utc
        ).isoformat()

    if not product["id"]:
        return None

    if not product["name"]:
        return None

    if not product["url"]:
        return None

    if not product["image"]:
        product["image"] = ""

    if not product["price"]:
        product["price_verified"] = False

    return product


def main():
    rows = read_csv()

    products = []
    seen_ids = set()

    ignored = 0

    for row in rows:
        product = convert_product(row)

        if product is None:
            ignored += 1
            continue

        product_id = product["id"]

        if product_id in seen_ids:
            ignored += 1
            continue

        seen_ids.add(product_id)
        products.append(product)

    JSON_FILE.write_text(
        json.dumps(
            products,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    with_price = sum(
        1 for product in products
        if product["price"]
    )

    with_image = sum(
        1 for product in products
        if product["image"]
    )

    print("IMPORTATION TERMINÉE")
    print("--------------------")
    print(f"Produits importés : {len(products)}")
    print(f"Produits avec prix : {with_price}")
    print(f"Produits avec image : {with_image}")
    print(f"Produits sans prix : {len(products) - with_price}")
    print(f"Produits ignorés : {ignored}")
    print(f"Fichier créé : {JSON_FILE.name}")


if __name__ == "__main__":
    main()
