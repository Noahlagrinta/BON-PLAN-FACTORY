
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
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


def detect_delimiter(sample):
    """Détecte le séparateur du fichier CSV."""
    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=",;\t"
        )
        return dialect.delimiter
    except csv.Error:
        return ","


def valid_url(value):
    """Vérifie qu'une URL est valide."""
    value = (value or "").strip()

    if not value:
        return ""

    parsed = urlparse(value)

    if parsed.scheme not in ("http", "https"):
        return ""

    if not parsed.netloc:
        return ""

    return value


def clean_price(value):
    """Nettoie un prix sans inventer de valeur."""
    value = (value or "").strip()

    if not value:
        return ""

    value = value.replace("€", "")
    value = value.replace("EUR", "")
    value = value.replace(" ", "")
    value = value.replace(",", ".")

    try:
        number = float(value)

        if number < 0:
            return ""

        return str(number)

    except ValueError:
        return ""


def read_csv():
    """Lit le catalogue CSV et vérifie ses colonnes."""

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {CSV_FILE}"
        )

    content = CSV_FILE.read_text(
        encoding="utf-8-sig"
    )

    if not content.strip():
        raise ValueError(
            "Le fichier product_feed.csv est vide."
        )

    # Détecte le séparateur à partir du début du fichier.
    sample = content[:8192]
    delimiter = detect_delimiter(sample)

    reader = csv.DictReader(
        content.splitlines(),
        delimiter=delimiter
    )

    if not reader.fieldnames:
        raise ValueError(
            "Aucun en-tête trouvé dans product_feed.csv."
        )

    # Nettoie les noms des colonnes.
    reader.fieldnames = [
        (name or "").strip().lower()
        for name in reader.fieldnames
    ]

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in reader.fieldnames
    ]

    if missing:
        raise ValueError(
            "Colonnes manquantes dans product_feed.csv : "
            + ", ".join(missing)
        )

    rows = []

    for row in reader:
        cleaned = {}

        for key, value in row.items():
            if key:
                cleaned[key.strip().lower()] = (
                    value.strip() if value else ""
                )

        rows.append(cleaned)

    return rows


def convert_product(row):
    """Transforme une ligne CSV en produit JSON."""

    product_id = row.get("id", "").strip()
    name = row.get("name", "").strip()
    url = valid_url(row.get("url", ""))

    if not product_id or not name or not url:
        return None

    price = clean_price(row.get("price", ""))

    image = valid_url(row.get("image", ""))

    checked_at = row.get("checked_at", "").strip()

    if not checked_at:
        checked_at = datetime.now(
            timezone.utc
        ).isoformat()

    product = {
        "id": product_id,
        "name": name,
        "brand": row.get("brand", "").strip(),
        "category": row.get("category", "").strip(),
        "image": image,
        "merchant": row.get("merchant", "").strip(),
        "price": price,
        "currency": (
            row.get("currency", "").strip() or "EUR"
        ),
        "url": url,
        "checked_at": checked_at,
        "description": row.get("description", "").strip(),
        "old_price": clean_price(row.get("old_price", "")),
        "price_verified": (
            row.get("price_verified", "").strip().lower()
            in ("true", "1", "yes", "oui")
        ),
    }

    if not price:
        product["price_verified"] = False

    return product


def main():
    print("Lecture du catalogue produits...")

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

    JSON_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with JSON_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            indent=2
        )

    with_price = sum(
        1 for product in products
        if product["price"]
    )

    with_image = sum(
        1 for product in products
        if product["image"]
    )

    print("--------------------------------")
    print("IMPORTATION TERMINÉE")
    print("--------------------------------")
    print(f"Produits importés : {len(products)}")
    print(f"Avec prix : {with_price}")
    print(f"Avec image : {with_image}")
    print(f"Sans prix : {len(products) - with_price}")
    print(f"Lignes ignorées : {ignored}")
    print("--------------------------------")


if __name__ == "__main__":
    main()
