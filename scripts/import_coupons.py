
import json
import re
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

API_URL = "https://partners.clickwise.net/api/v1/deals/?lang=fr&page_size=100"
OUTPUT = Path("coupons.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 BON-PLAN-FACTORY/1.0",
    "Accept": "application/json"
}

# Devises acceptées pour le marché français
ALLOWED_CURRENCIES = {"", "EUR"}

# Marchands et offres à exclure explicitement
EXCLUDED_TERMS = [
    "dji usa",
    "hulu",
    "noon food",
    "deliveroo",
    "hong kong",
    "hk$",
    "aed",
    "brl",
    "casa security",
    "approval required"
]

def is_french_offer(offer):
    text = " ".join(str(offer.get(k, "")) for k in [
        "merchant_name", "title", "description"
    ]).lower()

    if any(term in text for term in EXCLUDED_TERMS):
        return False

    currency = str(offer.get("discount_currency") or "").upper()

    if currency not in ALLOWED_CURRENCIES:
        return False

    return True

def get_discount(offer):
    value = offer.get("discount_pct")

    if value is None:
        return None

    try:
        discount = float(value)
    except (TypeError, ValueError):
        return None

    if not 20 <= discount <= 100:
        return None

    return discount

def main():
    request = urllib.request.Request(API_URL, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        raw_data = json.loads(response.read().decode("utf-8"))

    source_offers = raw_data.get("results", [])

    coupons = []
    seen = set()

    for offer in source_offers:
        merchant = str(offer.get("merchant_name") or "").strip()
        title = str(offer.get("title") or "").strip()
        url = str(offer.get("url") or "").strip()
        code = str(offer.get("code") or "").strip()

        discount = get_discount(offer)

        if not merchant or not title or not url:
            continue

        if not url.startswith("https://"):
            continue

        if not discount or not is_french_offer(offer):
            continue

        unique_id = str(offer.get("id") or url)

        if unique_id in seen:
            continue

        seen.add(unique_id)

        coupons.append({
            "id": unique_id,
            "merchant": merchant,
            "title": title,
            "code": code,
            "discount_percent": discount,
            "discount_amount": offer.get("discount_amount"),
            "discount_currency": offer.get("discount_currency") or "EUR",
            "valid_until": offer.get("valid_until"),
            "url": url,
            "checked_at": datetime.now(timezone.utc).isoformat()
        })

    coupons.sort(
        key=lambda item: item["discount_percent"],
        reverse=True
    )

    data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "coupons": coupons
    }

    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"{len(coupons)} offres françaises filtrées.")

if __name__ == "__main__":
    main()
