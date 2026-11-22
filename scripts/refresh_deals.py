
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEALS_FILE = ROOT / "deals.json"

def main():
    if not DEALS_FILE.exists():
        raise FileNotFoundError("deals.json introuvable")

    with DEALS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    now = datetime.now(timezone.utc)
    valid_offers = []

    for offer in data.get("offers", []):
        try:
            original = float(offer["original_price"])
            sale = float(offer["sale_price"])

            if original <= 0 or sale <= 0 or sale >= original:
                continue

            discount = round((1 - sale / original) * 100)

            if discount < 20:
                continue

            if not offer.get("title") or not offer.get("store"):
                continue

            if not offer.get("category") or not offer.get("url"):
                continue

            if not offer["url"].startswith(("https://", "http://")):
                continue

            expiry = offer.get("expires_at")
            if expiry:
                expiry_date = datetime.fromisoformat(
                    expiry.replace("Z", "+00:00")
                )
                if expiry_date.tzinfo is None:
                    expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                if expiry_date <= now:
                    continue

            offer["discount_percent"] = discount
            valid_offers.append(offer)

        except (KeyError, ValueError, TypeError):
            continue

    valid_offers.sort(
        key=lambda offer: (
            float(offer.get("featured_score", 0)),
            float(offer.get("discount_percent", 0))
        ),
        reverse=True
    )

    data["offers"] = valid_offers
    data["last_updated"] = now.isoformat()

    with DEALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print(f"Nettoyage terminé : {len(valid_offers)} offre(s) conservée(s).")

if __name__ == "__main__":
    main()

