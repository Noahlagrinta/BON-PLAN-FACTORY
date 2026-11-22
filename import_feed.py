
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = ROOT / "product_feed.json"
DEALS_FILE = ROOT / "deals.json"

def load_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def is_available_in_france(offer):
    country = str(offer.get("country", "")).upper()
    countries = [
        str(item).upper()
        for item in offer.get("shipping_countries", [])
    ]
    return country == "FR" or "FR" in countries

def main():
    if not FEED_FILE.exists():
        print("Aucun flux produit connecté pour le moment.")
        return

    feed = load_json(FEED_FILE, {})
    deals = load_json(DEALS_FILE, {"last_updated": None, "offers": []})

    existing = {
        offer.get("url"): offer
        for offer in deals.get("offers", [])
        if offer.get("url")
    }

    imported = 0
    now = datetime.now(timezone.utc)

    for item in feed.get("offers", []):
        try:
            title = str(item["title"]).strip()
            store = str(item["store"]).strip()
            category = str(item["category"]).strip()
            url = str(item["url"]).strip()

            original = float(item["original_price"])
            sale = float(item["sale_price"])
            currency = str(item.get("currency", "EUR")).upper()

            if not title or not store or not category:
                continue
            if not url.startswith(("https://", "http://")):
                continue
            if original <= 0 or sale <= 0 or sale >= original:
                continue
            if currency != "EUR":
                continue
            if not is_available_in_france(item):
                continue

            discount = round((1 - sale / original) * 100)
            if discount < 20:
                continue

            expiry = item.get("expires_at")
            if expiry:
                expiry_date = datetime.fromisoformat(
                    expiry.replace("Z", "+00:00")
                )
                if expiry_date.tzinfo is None:
                    expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                if expiry_date <= now:
                    continue

            offer = {
                "title": title,
                "store": store,
                "category": category,
                "url": url,
                "original_price": original,
                "sale_price": sale,
                "discount_percent": discount,
                "currency": "EUR",
                "image_url": item.get("image_url", ""),
                "country": "FR",
                "expires_at": expiry,
                "checked_at": now.isoformat(),
                "featured_score": float(item.get("featured_score", 0))
            }

            existing[url] = offer
            imported += 1

        except (KeyError, ValueError, TypeError, AttributeError):
            continue

    deals["offers"] = list(existing.values())
    deals["last_updated"] = now.isoformat()

    with DEALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(deals, file, ensure_ascii=False, indent=2)

    print(f"Import terminé : {imported} offre(s) importée(s).")

if __name__ == "__main__":
    main()
