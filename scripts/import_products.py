
import csv
import json
import io
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CSV_FILE = ROOT / "product_feed.csv"
JSON_FILE = ROOT / "product_feed.json"

REQUIRED_COLUMNS = [
    "id", "name", "brand", "category", "image",
    "merchant", "price", "currency", "url", "checked_at"
]


def valid_url(value):
    value = (value or "").strip()

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
    value = (value or "").strip()
    value = value.replace("€", "").replace("EUR", "")
    value = value.replace(" ", "").replace(",", ".")

    if not value:
        return ""

    try:
        number = float(value)
        return str(number) if number >= 0 else ""
    except ValueError:
        return ""


def read_csv():
    print("Recherche du fichier CSV...")
    print(f"Dossier du projet : {ROOT}")
    print(f"Fichier recherché : {CSV_FILE}")
    print(f"Fichier présent : {CSV_FILE.exists()}")

    if not CSV_FILE.exists():
        raise FileNotFoundError(
            f"Impossible de trouver {CSV_FILE}"
        )

    content = CSV_FILE.read_text(encoding="utf-8-sig")

    print(f"Taille du fichier : {len(content)} caractères")
    print(f"Début du fichier : {repr(content[:250])}")

    if not content.strip():
        raise ValueError(
            "Le fichier product_feed.csv est vide dans GitHub Actions."
        )

    # Normalisation des retours à la ligne.
    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # Recherche de la première ligne non vide.
    lines = content.split("\n")
    first_line = next(
        (line for line in lines if line.strip()),
        ""
    )

    if not first_line:
        raise ValueError("Aucune ligne CSV exploitable.")

    # Détection du séparateur.
    if first_line.count(";") > first_line.count(","):
        delimiter = ";"
    elif first_line.count("\t") > first_line.count(","):
        delimiter = "\t"
    else:
        delimiter = ","

    print(f"Séparateur détecté : {repr(delimiter)}")

    stream = io.StringIO(content, newline="")

    reader = csv.DictReader(
        stream,
        delimiter=delimiter
    )

    if not reader.fieldnames:
        raise ValueError(
            "En-tête introuvable. Vérifie le contenu affiché "
            "dans les logs juste au-dessus."
        )

    reader.fieldnames = [
        (name or "").strip().lower().lstrip("\ufeff")
        for name in reader.fieldnames
    ]

    print(f"En-têtes détectés : {reader.fieldnames}")

    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in reader.fieldnames
    ]

    if missing:
        raise ValueError(
            "Colonnes manquantes : " + ", ".join(missing)
        )

    rows = []

    for row in reader:
        cleaned = {
            (key or "").strip().lower(): (
                value.strip() if value else ""
            )
            for key, value in row.items()
            if key is not None
        }

        rows.append(cleaned)

    return rows


def convert_product(row):
    product_id = row.get("id", "").strip()
    name = row.get("name", "").strip()
    url = valid_url(row.get("url", ""))

    if not product_id or not name or not url:
        return None

    price = clean_price(row.get("price", ""))

    checked_at = row.get("checked_at", "").strip()

    if not checked_at:
        checked_at = datetime.now(
            timezone.utc
        ).isoformat()

    price_verified = (
        row.get("price_verified", "").strip().lower()
        in ("true", "1", "yes", "oui")
    )

    if not price:
        price_verified = False

    return {
        "id": product_id,
        "name": name,
        "brand": row.get("brand", "").strip(),
        "category": row.get("category", "").strip(),
        "image": valid_url(row.get("image", "")),
        "merchant": row.get("merchant", "").strip(),
        "price": price,
        "currency": row.get("currency", "").strip() or "EUR",
        "url": url,
        "checked_at": checked_at,
        "description": row.get("description", "").strip(),
        "old_price": clean_price(row.get("old_price", "")),
        "price_verified": price_verified
    }


def main():
    print("LECTURE DU CATALOGUE PRODUITS")

    rows = read_csv()

    products = []
    seen_ids = set()
    ignored = 0

    for row in rows:
        product = convert_product(row)

        if product is None:
            ignored += 1
            continue

        if product["id"] in seen_ids:
            ignored += 1
            continue

        seen_ids.add(product["id"])
        products.append(product)

    JSON_FILE.parent.mkdir(parents=True, exist_ok=True)

    with JSON_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            indent=2
        )

    with_price = sum(bool(p["price"]) for p in products)
    with_image = sum(bool(p["image"]) for p in products)

    print("--------------------------------")
    print("IMPORTATION TERMINÉE")
    print("--------------------------------")
    print(f"Produits importés : {len(products)}")
    print(f"Avec prix : {with_price}")
    print(f"Avec images : {with_image}")
    print(f"Sans prix : {len(products) - with_price}")
    print(f"Lignes ignorées : {ignored}")
    print("--------------------------------")


if __name__ == "__main__":
    main()
