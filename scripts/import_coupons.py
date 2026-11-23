
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, date
from urllib.parse import urlparse

API_URL = "https://partners.clickwise.net/api/v1/deals/?lang=fr&page_size=100"
OUTPUT = Path("coupons.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 BON-PLAN-FACTORY/1.0",
    "Accept": "application/json"
}

# On accepte uniquement les réductions explicitement exprimées en euros.
ALLOWED_CURRENCIES = {"EUR"}

MIN_DISCOUNT = 20
MAX_DISCOUNT = 100

INVALID_CODES = {
    "", "none", "null", "n/a", "na",
    "no code", "no code required", "undefined"
}


def clean(value):
    return str(value or "").strip()


def valid_url(value):
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https"
            and bool(parsed.netloc)
        )
    except Exception:
        return False


def parse_expiry(value):
    """
    Retourne :
    - True si la date est encore valable
    - False si elle est dépassée
    - None si aucune date exploitable n'est fournie
    """
    if not value:
        return None

    raw = clean(value)

    try:
        expiry = datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        )

        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        return expiry >= datetime.now(timezone.utc)

    except ValueError:
        pass

    try:
        expiry_date = date.fromisoformat(raw[:10])
        return expiry_date >= datetime.now(timezone.utc).date()

    except ValueError:
        return None


def main():
    request = urllib.request.Request(
        API_URL,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        data = json.loads(
            response.read().decode("utf-8")
        )

    results = data.get("results")

    if not isinstance(results, list):
        raise RuntimeError(
            "Réponse Clickwise inattendue : "
            "la liste des offres est introuvable."
        )

    if not results:
        raise RuntimeError(
            "Clickwise n'a renvoyé aucune offre. "
            "Le fichier existant est conservé."
        )

    coupons = []
    seen = set()

    now = datetime.now(timezone.utc).isoformat()

    for offer in results:
        merchant = clean(
            offer.get("merchant_name")
        )

        title = clean(
            offer.get("title")
        )

        url = clean(
            offer.get("url")
        )

        code = clean(
            offer.get("code")
        )

        currency = clean(
            offer.get("discount_currency")
        ).upper()

        valid_until = offer.get("valid_until")

        # Informations indispensables.
        if not merchant or not title or not valid_url(url):
            continue

        # Un véritable code promo est obligatoire.
        if code.lower() in INVALID_CODES:
            continue

        # Pas de devise inconnue ou supposée en euros.
        if currency not in ALLOWED_CURRENCIES:
            continue

        try:
            discount = float(
                offer.get("discount_pct")
            )
        except (TypeError, ValueError):
            continue

        if not MIN_DISCOUNT <= discount <= MAX_DISCOUNT:
            continue

        # Écarter les codes dont la date d'expiration est dépassée.
        expiry_status = parse_expiry(valid_until)

        if expiry_status is False:
            continue

        offer_id = clean(
            offer.get("id")
        ) or url

        if offer_id in seen:
            continue

        seen.add(offer_id)

        coupons.append({
            "id": offer_id,
            "merchant": merchant,
            "title": title,
            "code": code,
            "discount_percent": discount,
            "discount_amount": offer.get("discount_amount"),
            "discount_currency": "EUR",
            "valid_until": valid_until,
            "validity_status": (
                "date_not_provided"
                if expiry_status is None
                else "valid_at_import"
            ),
            "url": url,
            "source": "Clickwise",
            "checked_at": now
        })

    coupons.sort(
        key=lambda item: item["discount_percent"],
        reverse=True
    )

    output_data = {
        "last_updated": now,
        "coupons": coupons
    }

    OUTPUT.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"{len(coupons)} codes promo utilisables "
        "retenus après filtrage."
    )

    print(
        "Offres reçues de Clickwise : "
        f"{len(results)}"
    )

    print(
        "Codes sans devise EUR, sans code ou expirés : "
        f"{len(results) - len(coupons)} écartés."
    )


if __name__ == "__main__":
    main()
