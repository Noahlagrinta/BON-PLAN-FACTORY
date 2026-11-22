
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

API_URL = "https://partners.clickwise.net/api/v1/deals/?lang=fr&page_size=100"
OUTPUT = Path("coupons.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 BON-PLAN-FACTORY/1.0",
    "Accept": "application/json"
}

ALLOWED_CURRENCIES = {"", "EUR"}

EXCLUDED_TERMS = [
    "dji usa", "hulu", "noon food", "hong kong",
    "approval required"
]

def main():
    request = urllib.request.Request(API_URL, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    coupons = []
    seen = set()

    for offer in data.get("results", []):
        merchant = str(offer.get("merchant_name") or "").strip()
        title = str(offer.get("title") or "").strip()
        url = str(offer.get("url") or "").strip()
        currency = str(offer.get("discount_currency") or "").upper()

        try:
            discount = float(offer.get("discount_pct"))
        except (TypeError, ValueError):
            continue

        text = (merchant + " " + title).lower()

        if not merchant or not title or not url.startswith("https://"):
            continue

        if currency not in ALLOWED_CURRENCIES:
            continue

        if any(term in text for term in EXCLUDED_TERMS):
            continue

        if not 20 <= discount <= 100:
            continue

        offer_id = str(offer.get("id") or url)

        if offer_id in seen:
            continue

        seen.add(offer_id)

        coupons.append({
            "id": offer_id,
            "merchant": merchant,
            "title": title,
            "code": str(offer.get("code") or ""),
            "discount_percent": discount,
            "discount_amount": offer.get("discount_amount"),
            "discount_currency": currency or "EUR",
            "valid_until": offer.get("valid_until"),
            "url": url,
            "checked_at": datetime.now(timezone.utc).isoformat()
        })

    coupons.sort(key=lambda item: item["discount_percent"], reverse=True)

    OUTPUT.write_text(
        json.dumps({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "coupons": coupons
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"{len(coupons)} offres retenues.")

if __name__ == "__main__":
    main()
