
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
COUPONS_FILE = ROOT / "coupons.json"

API_URL = (
    "https://partners.clickwise.net/api/v1/deals/"
    "?lang=fr&page_size=50"
)


def main():
    request = Request(
        API_URL,
        headers={"User-Agent": "BonPlanFactory/1.0"}
    )

    with urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    results = data.get("results", [])
    now = datetime.now(timezone.utc)
    coupons = {}

    for deal in results:
        try:
            valid_until = deal.get("valid_until")

            if valid_until:
                expiry = datetime.fromisoformat(
                    valid_until.replace("Z", "+00:00")
                )
                if expiry.tzinfo is None:
                    expiry = expiry.replace(tzinfo=timezone.utc)
                if expiry <= now:
                    continue

            deal_url = deal.get("url", "")
            if deal_url.startswith("/"):
                deal_url = (
                    "https://partners.clickwise.net" + deal_url
                )

            if not deal_url.startswith("https://"):
                continue

            coupon = {
                "id": str(deal.get("id", "")),
                "merchant": deal.get("merchant_name", ""),
                "title": deal.get("title", ""),
                "code": deal.get("code") or "",
                "discount_percent": deal.get("discount_pct"),
                "discount_amount": deal.get("discount_amount"),
                "discount_currency": deal.get("discount_currency"),
                "valid_until": valid_until,
                "url": deal_url,
                "checked_at": now.isoformat()
            }

            if not coupon["merchant"] or not coupon["title"]:
                continue

            coupons[coupon["id"]] = coupon

        except (ValueError, TypeError, AttributeError):
            continue

    output = {
        "last_updated": now.isoformat(),
        "coupons": list(coupons.values())
    }

    with COUPONS_FILE.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"{len(coupons)} code(s) ou offre(s) conservé(s).")


if __name__ == "__main__":
    main()
