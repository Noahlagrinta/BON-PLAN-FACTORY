
import json
import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urljoin

FEED_URL = "https://www.dealabs.com/rss/hot"
OUTPUT = Path("deals.json")
MAX_OFFERS = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 BON-PLAN-FACTORY/1.0"
}

CATEGORIES = {
    "Gaming": ["gaming", "playstation", "xbox", "nintendo", "steam"],
    "High-tech": ["smartphone", "iphone", "samsung", "ordinateur", "pc portable"],
    "Mode & sneakers": ["nike", "adidas", "sneakers", "chaussures", "vêtement"],
    "Football": ["football", "crampons", "maillot"],
    "Basketball": ["basketball", "basket", "nba"],
    "Impression 3D": ["imprimante 3d", "filament", "creality", "elegoo", "bambu"],
    "Musique & studio": ["microphone", "micro", "enceinte", "studio", "casque audio"],
    "LEGO & loisirs": ["lego", "jouet", "construction"],
    "Création de contenu": ["caméra", "camera", "streaming", "appareil photo"]
}

def clean(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

def category_of(value):
    value = value.lower()
    for category, keywords in CATEGORIES.items():
        if any(word in value for word in keywords):
            return category
    return "Autres bons plans"

def get_tag(item, name):
    for child in item.iter():
        if child.tag.split("}")[-1].lower() == name.lower():
            return "".join(child.itertext()).strip()
    return ""

def get_image(item, description):
    for child in item.iter():
        if child.tag.split("}")[-1].lower() in ("thumbnail", "content", "enclosure"):
            url = child.attrib.get("url", "")
            if url.startswith("https://"):
                return url

    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        description or "",
        re.IGNORECASE
    )

    if match and match.group(1).startswith("https://"):
        return html.unescape(match.group(1))

    return ""

def get_prices(title, description):
    combined = title + " " + clean(description)

    percent_match = re.search(r'(?:-|−)\s*(\d{1,2})\s*%', combined)
    percent = int(percent_match.group(1)) if percent_match else None

    money = r'(?<!\w)(\d{1,5}(?:[ .]\d{3})*(?:[,.]\d{1,2})?)\s*(?:€|EUR)'

    old_price = None
    old_tags = re.findall(
        r'<(?:del|s|strike)[^>]*>(.*?)</(?:del|s|strike)>',
        description or "",
        re.IGNORECASE | re.DOTALL
    )

    if old_tags:
        match = re.search(money, clean(" ".join(old_tags)))
        if match:
            old_price = float(
                match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
            )

    prices = re.findall(money, combined)
    if not prices:
        return None, None, None

    sale = float(prices[0].replace(" ", "").replace(".", "").replace(",", "."))

    if old_price and old_price > sale:
        percent = round((1 - sale / old_price) * 100)
        return old_price, sale, percent

    if percent and 0 < percent < 100:
        original = round(sale / (1 - percent / 100), 2)
        return original, sale, percent

    return None, None, None

def main():
    request = urllib.request.Request(FEED_URL, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        root = ET.fromstring(response.read())

    offers = []
    seen = set()

    for item in root.iter():
        if item.tag.split("}")[-1].lower() != "item":
            continue

        title = get_tag(item, "title")
        url = get_tag(item, "link")
        description = get_tag(item, "description")

        if not title or not url:
            continue

        url = urljoin(FEED_URL, url)

        if not url.startswith("https://") or url in seen:
            continue

        original, sale, discount = get_prices(title, description)

        if not original or not sale or not discount or discount < 20:
            continue

        if sale >= original:
            continue

        seen.add(url)

        offers.append({
            "title": clean(title),
            "store": "Dealabs",
            "source": "Dealabs",
            "url": url,
            "image": get_image(item, description),
            "category": category_of(title + " " + description),
            "original_price": original,
            "sale_price": sale,
            "discount_percent": discount,
            "featured_score": discount
        })

    offers.sort(key=lambda offer: offer["featured_score"], reverse=True)

    OUTPUT.write_text(
        json.dumps({
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "offers": offers[:MAX_OFFERS]
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"{len(offers[:MAX_OFFERS])} promotions importées.")

if __name__ == "__main__":
    main()
