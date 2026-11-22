
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEALS_FILE = ROOT / "deals.json"


def safe_number(value, default=0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def main():
    if not DEALS_FILE.exists():
        raise FileNotFoundError("deals.json introuvable.")

    with DEALS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    now = datetime.now(timezone.utc)
    valid_offers = []

    for offer in data.get("offers", []):
        if not isinstance(offer, dict):
            continue

        try:
            original = float(offer["original_price"])
            sale = float(offer["sale_price"])

            if original <= 0 or sale <= 0 or sale >= original:
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
                    expiry_date = expiry_date.replace(
                        tzinfo=timezone.utc
                    )
                if expiry_date <= now:
                    continue

            discount = round((1 - sale / original) * 100)
            if discount < 20:
                continue

            offer["discount_percent"] = discount
            valid_offers.append(offer)

        except (KeyError, ValueError, TypeError, AttributeError):
            continue

    valid_offers.sort(
        key=lambda item: (
            safe_number(item.get("featured_score")),
            safe_number(item.get("discount_percent"))
        ),
        reverse=True
    )

    data["offers"] = valid_offers
    data["last_updated"] = now.isoformat()

    with DEALS_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

    print(
        f"Nettoyage terminé : "
        f"{len(valid_offers)} offre(s) conservée(s)."
    )


if __name__ == "__main__":
    main()
