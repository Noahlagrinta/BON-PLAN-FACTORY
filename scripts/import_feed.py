
import json
import re
import html
import urllib.request
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

FEED_URL = "https://www.dealabs.com/rss/hot"
OUTPUT = Path("deals.json")
MAX_OFFERS = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 BON-PLAN-FACTORY/1.0"
}

CATEGORIES = {
    "Impression 3D": [
        "imprimante 3d", "impression 3d", "filament",
        "creality", "elegoo", "bambu lab"
    ],
    "Basketball": [
        "basketball", "basket ball", "nba",
        "ballon de basket", "chaussure de basket"
    ],
    "Football": [
        "football", "crampons", "maillot de foot",
        "ballon de football"
    ],
    "Musique & studio": [
        "musique", "microphone", "micro",
        "enceinte", "studio", "casque audio",
        "guitare", "clavier midi", "dj"
    ],
    "Création de contenu": [
        "streaming", "webcam", "ring light",
        "camera", "caméra", "appareil photo",
        "capture card"
    ],
    "LEGO & loisirs": [
        "lego", "jouet", "construction",
        "maquette", "jeu de société"
    ],
    "Gaming": [
        "gaming", "playstation", "xbox",
        "nintendo", "steam", "manette",
        "console", "jeu video", "jeu vidéo"
    ],
    "Mode & sneakers": [
        "nike", "adidas", "puma", "sneakers",
        "chaussures", "vêtement", "vêtements",
        "new balance", "asics"
    ],
    "High-tech": [
        "smartphone", "iphone", "samsung",
        "ordinateur", "pc portable", "tablette",
        "ssd", "disque dur", "écran", "moniteur"
    ]
}


def clean(value):
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize(value):
    value = clean(value).lower()
    value = value.replace("é", "e").replace("è", "e")
    value = value.replace("ê", "e").replace("ë", "e")
    value = value.replace("à", "a").replace("â", "a")
    value = value.replace("î", "i").replace("ï", "i")
    value = value.replace("ô", "o").replace("ù", "u")
    return value


def category_of(value):
    text = normalize(value)

    scores = {}

    for category, keywords in CATEGORIES.items():
        score = 0

        for keyword in keywords:
            keyword = normalize(keyword)

            if keyword in text:
                score += 2 if " " in keyword else 1

        if score:
            scores[category] = score

    if not scores:
        return "Autres bons plans"

    return max(scores, key=scores.get)


def get_tag(item, name):
    for child in item.iter():
        if child.tag.split("}")[-1].lower() == name.lower():
            return "".join(child.itertext()).strip()

    return ""


def get_image(item, description):
    for child in item.iter():
        tag = child.tag.split("}")[-1].lower()

        if tag in ("thumbnail", "content", "enclosure"):
            url = child.attrib.get("url", "")

            if url.startswith("https://"):
                return url

    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        description or "",
        re.IGNORECASE
    )

    if match:
        url = html.unescape(match.group(1))

        if url.startswith("https://"):
            return url

    return ""


def parse_price(value):
    try:
        value = value.replace(" ", "").replace("\u202f", "")
        value = value.replace(".", "").replace(",", ".")
        return round(float(value), 2)
    except (ValueError, TypeError):
        return None


def get_prices(title, description):
    raw = html.unescape(description or "")

    money = (
        r'(?<!\w)(\d{1,5}(?:[ .\u202f]\d{3})*'
        r'(?:[,.]\d{1,2})?)\s*(?:€|EUR)'
    )

    old_price = None

    old_tags = re.findall(
        r'<(?:del|s|strike)[^>]*>(.*?)</(?:del|s|strike)>',
        raw,
        re.IGNORECASE | re.DOTALL
    )

    if old_tags:
        old_match = re.search(money, clean(" ".join(old_tags)))

        if old_match:
            old_price = parse_price(old_match.group(1))

    without_old = re.sub(
        r'<(?:del|s|strike)[^>]*>.*?</(?:del|s|strike)>',
        " ",
        raw,
        flags=re.IGNORECASE | re.DOTALL
    )

    remaining = clean(without_old)
    prices = re.findall(money, remaining)

    sale_price = parse_price(prices[0]) if prices else None

    discount = None

    if (
        old_price is not None
        and sale_price is not None
        and old_price > sale_price > 0
    ):
        discount = round(
            (1 - sale_price / old_price) * 100
        )

        return old_price, sale_price, discount, True

    # Ne jamais inventer un ancien prix.
    # Sans deux prix explicites, on ne confirme pas le prix barré.
    return None, sale_price, None, False


def get_store(title, description):
    text = clean(title + " " + description)

    patterns = [
        r'\bchez\s+([A-Z0-9][A-Za-z0-9 .&\'-]{1,35})',
        r'\bsur\s+([A-Z0-9][A-Za-z0-9 .&\'-]{1,35})'
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            store = match.group(1).strip(" .,-")

            if store:
                return store

    return "Magasin à identifier"


def valid_url(url):
    parsed = urlparse(url)

    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
    )


def main():
    request = urllib.request.Request(
        FEED_URL,
        headers=HEADERS
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:
        root = ET.fromstring(response.read())

    offers = []
    seen = set()

    for item in root.iter():
        if item.tag.split("}")[-1].lower() != "item":
            continue

        title = clean(get_tag(item, "title"))
        url = get_tag(item, "link")
        description = get_tag(item, "description")

        if not title or not url:
            continue

        url = urljoin(FEED_URL, url)

        if not valid_url(url) or url in seen:
            continue

        original, sale, discount, price_verified = get_prices(
            title,
            description
        )

        image = get_image(item, description)

        category = category_of(
            title + " " + clean(description)
        )

        store = get_store(title, description)

        seen.add(url)

        offers.append({
            "title": title,
            "store": store,
            "source": "Dealabs",
            "url": url,
            "image": image,
            "category": category,
            "original_price": original,
            "sale_price": sale,
            "discount_percent": discount,
            "price_verified": price_verified,
            "featured_score": discount or 0
        })

    if not offers:
        raise RuntimeError(
            "Aucune offre récupérée. "
            "Le fichier existant est conservé."
        )

    offers.sort(
        key=lambda offer: offer["featured_score"],
        reverse=True
    )

    data = {
        "last_updated": datetime.now(
            timezone.utc
        ).isoformat(),
        "offers": offers[:MAX_OFFERS]
    }

    OUTPUT.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        f"{len(offers[:MAX_OFFERS])} offres importées."
    )

    print(
        "Prix explicitement confirmés : "
        f"{sum(1 for o in offers if o['price_verified'])}"
    )


if __name__ == "__main__":
    main()
