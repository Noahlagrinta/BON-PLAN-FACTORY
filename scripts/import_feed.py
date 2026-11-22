
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEED_FILE = ROOT / "product_feed.json"
DEALS_FILE = ROOT / "deals.json"


def read_json(path, default):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def available_in_france(item):
    country = str(item.get("country", "")).upper()
    shipping = item.get("shipping_countries", [])
    if not isinstance(shipping, list):
        shipping = []
    shipping = [str(value).upper() for value in shipping]
    return country == "FR" or "FR" in shipping


def main():
    if not FEED_FILE.exists():
        print("Aucun fichier product_feed.json trouvé.")
        return

    feed = read_json(FEED_FILE, {"offers": []})
    deals = read_json(DEALS_FILE, {
        "last_updated": None,
        "offers": []
    })

    if not isinstance(feed, dict) or not isinstance(deals, dict):
        raise ValueError("Format JSON incorrect.")

    current = {}
    for offer in deals.get("offers", []):
        if isinstance(offer, dict) and offer.get("url"):
            current[offer["url"]] = offer

    imported = 0
    now = datetime.now(timezone.utc)

    for item in feed.get("offers", []):
        if not isinstance(item, dict):
            continue

        try:
            title = str(item["title"]).strip()
            store = str(item["store"]).strip()
            category = str(item["category"]).strip()
            url = str(item["url"]).strip()

            original = float(item["original_price"])
            sale = float(item["sale_price"])
            currency = str(item.get("currency", "EUR")).upper()

            if not all([title, store, category]):
                continue
            if not url.startswith(("https://", "http://")):
                continue
            if currency != "EUR":
                continue
            if original <= 0 or sale <= 0 or sale >= original:
                continue
            if not available_in_france(item):
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
                    expiry_date = expiry_date.replace(
                        tzinfo=timezone.utc
                    )
                if expiry_date <= now:
                    continue

            current[url] = {
                "title": title,
                "store": store,
                "category": category,
                "url": url,
                "original_price": original,
                "sale_price": sale,
                "discount_percent": discount,
                "currency": "EUR",
                "image_url": item.get("image_url", ""),
                "expires_at": expiry,
                "checked_at": now.isoformat(),
                "featured_score": item.get("featured_score", 0)
            }
            imported += 1

        except (KeyError, ValueError, TypeError, AttributeError):
            continue

    deals["offers"] = list(current.values())
    deals["last_updated"] = now.isoformat()

    with DEALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(deals, file, ensure_ascii=False, indent=2)

    print(f"Import terminé : {imported} offre(s) importée(s).")


if __name__ == "__main__":
    main()
