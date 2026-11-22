
import json
import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin

FEED_URL = "https://www.dealabs.com/rss/hot"
OUTPUT = Path("deals.json")
MAX_OFFERS = 50

HEADERS = {
    "User-Agent": "Mozilla/5.0 BON-PLAN-FACTORY/1.0"
}

def text_of(element, name):
    for child in element.iter():
        if child.tag.split("}")[-1].lower() == name.lower():
            return "".join(child.itertext()).strip()
    return ""

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()

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

def get_prices(title, description):
    combined = title + " " + clean_text(description)

    percent_match = re.search(
        r'(?:-|−)\s*(\d{1,2})\s*%',
        combined
    )

    percent = int(percent_match.group(1)) if percent_match else None

    money_pattern = r'(?<!\w)(\d{1,5}(?:[ .]\d{3})*(?:[,.]\d{1,2})?)\s*(?:€|EUR)'

    old_price = None

    old_tags = re.findall(
        r'<(?:del|s|strike)[^>]*>(.*?)</(?:del|s|strike)>',
        description or "",
        re.IGNORECASE | re.DOTALL
    )

    if old_tags:
        old_match = re.search(money_pattern, clean_text(" ".join(old_tags)))
        if old_match:
            old_price = float(
                old_match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
            )

    prices = re.findall(money_pattern, combined)

    if not prices:
        return None, None, None

    sale_price = float(
        prices[0].replace(" ", "").replace(".", "").replace(",", ".")
    )

    if old_price and old_price > sale_price:
        percent = round((1 - sale_price / old_price) * 100)
        return old_price, sale_price, percent

    if percent and 0 < percent < 100:
        original_price = round(sale_price / (1 - percent / 100), 2)
        return original_price, sale_price, percent

    return None, sale_price, None

def guess_category(text):
    value = text.lower()

    categories = {
        "Gaming": ["gaming", "playstation", "xbox", "nintendo", "steam", "jeu vidéo"],
        "High-tech": ["smartphone", "iphone", "samsung", "ordinateur", "pc portable", "tablette"],
        "Mode & sneakers": ["nike", "adidas", "sneakers", "chaussures", "vêtement"],
        "Football": ["football", "crampons", "maillot"],
        "Basketball": ["basketball", "basket", "nba"],
        "Impression 3D": ["imprimante 3d", "filament", "creality", "elegoo", "bambu lab"],
        "Musique & studio": ["microphone", "micro", "enceinte", "studio", "casque audio"],
        "LEGO & loisirs": ["lego", "jouet", "construction"],
        "Création de contenu": ["caméra", "camera", "streaming", "éclairage", "appareil photo"]
    }

    for category, keywords in categories.items():
        if any(word in value for word in keywords):
            return category

    return "Autres bons plans"

def main():
    request = urllib.request.Request(FEED_URL, headers=HEADERS)

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    offers = []
    seen = set()

    items = [
        element for element in root.iter()
        if element.tag.split("}")[-1].lower() == "item"
    ]

    for item in items:
        title = text_of(item, "title")
        url = text_of(item, "link")
        description = text_of(item, "description")

        if not title or not url:
            continue

        url = urljoin(FEED_URL, url)

        if not url.startswith("https://") or url in seen:
            continue

        seen.add(url)

        original, sale, discount = get_prices(title, description)

        # Ne publier comme réduction chiffrée
        # que les offres dont la remise est vérifiable.
        if not original or not sale or not discount or discount < 20:
            continue

        if sale >= original:
            continue

        image = get_image(item, description)

        offers.append({
            "title": clean_text(title),
            "store": "Dealabs",
            "source": "Dealabs",
            "url": url,
            "image": image,
            "category": guess_category(title + " " + description),
            "original_price": original,
            "sale_price": sale,
            "discount_percent": discount,
            "featured_score": discount
        })

    offers.sort(
        key=lambda offer: offer["featured_score"],
        reverse=True
    )

    data = {
        "last_updated": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "offers": offers[:MAX_OFFERS]
    }

    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"{len(data['offers'])} promotions vérifiables importées.")

if __name__ == "__main__":
    main()
