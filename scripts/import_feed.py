
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_FILE = ROOT / "product_feed.csv"
JSON_FILE = ROOT / "product_feed.json"
DEALS_FILE = ROOT / "deals.json"


def read_feed():
    if CSV_FILE.exists():
        with CSV_FILE.open("r", encoding="utf-8-sig", newline="") as file:
            sample = file.read(4096)
            file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            return list(csv.DictReader(file, dialect=dialect))

    if JSON_FILE.exists():
        with JSON_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data.get("offers", [])

    return []


def number(value):
    if value is None:
        return None
    match = re.search(r"\d+(?:[.,]\d{1,2})?", str(value).replace(" ", ""))
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def main():
    if not DEALS_FILE.exists():
        raise FileNotFoundError("deals.json introuvable")

    with DEALS_FILE.open("r", encoding="utf-8") as file:
        deals = json.load(file)

    rows = read_feed()
    existing = {
        offer.get("url"): offer
        for offer in deals.get("offers", [])
        if offer.get("url")
    }

    imported = 0
    now = datetime.now(timezone.utc)

    for row in rows:
        try:
            title = str(row.get("title", "")).strip()
            store = str(
                row.get("seller_name") or row.get("store") or ""
            ).strip()

            url = str(
                row.get("clickwise_link")
                or row.get("link")
                or row.get("url")
                or ""
            ).strip()

            original = number(
                row.get("price") or row.get("original_price")
            )
            sale = number(
                row.get("sale_price") or row.get("sale")
            )

            currency = str(row.get("currency", "EUR")).upper()
            country = str(row.get("country", "FR")).upper()
            availability = str(row.get("availability", "")).lower()

            if not title or not store or not url:
                continue
            if not url.startswith(("https://", "http://")):
                continue
            if original is None or sale is None:
                continue
            if original <= 0 or sale <= 0 or sale >= original:
                continue
            if currency != "EUR" or country != "FR":
                continue
            if availability and availability not in (
                "in stock", "instock", "available", "en stock"
            ):
                continue

            discount = round((1 - sale / original) * 100)
            if discount < 20:
                continue

            category = str(
                row.get("category")
                or row.get("product_type")
                or "Autres"
            ).strip()

            image = str(
                row.get("image_link")
                or row.get("image")
                or row.get("image_url")
                or ""
            ).strip()

            existing[url] = {
                "title": title,
                "store": store,
                "category": category,
                "url": url,
                "original_price": original,
                "sale_price": sale,
                "discount_percent": discount,
                "currency": "EUR",
                "image_url": image,
                "checked_at": now.isoformat(),
                "featured_score": 0
            }
            imported += 1

        except (ValueError, TypeError, AttributeError):
            continue

    deals["offers"] = list(existing.values())
    deals["last_updated"] = now.isoformat()

    with DEALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(deals, file, ensure_ascii=False, indent=2)

    print(f"Import terminé : {imported} offre(s) importée(s).")


if __name__ == "__main__":
    main()
