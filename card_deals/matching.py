"""Turn a messy eBay title into a search query, and score PriceCharting matches."""

import re
import unicodedata
import urllib.parse

NOISE = {
    "psa", "gem", "mint", "mt", "graded", "grade", "slab", "slabbed", "card", "cards",
    "tcg", "ccg", "trading", "game", "nm", "near", "english", "eng", "en", "pop",
    "low", "hot", "invest", "grail", "wow", "look", "rare", "beautiful", "perfect",
    "free", "shipping", "ship", "fast", "auction", "no", "reserve", "new", "the",
    "and", "of", "w", "with", "case", "authentic", "cert", "pristine", "black", "label",
}
JAPANESE_RE = re.compile(r"\b(japanese|japan|jpn|jp)\b", re.I)

# Card-number patterns, most specific first.
NUMBER_PATTERNS = [
    re.compile(r"\b([A-Z0-9]{2,5}/[A-Z0-9]{2,5}-\d{2,3}[A-Z]*)\b"),           # Weiss: SAO/S20-001SP
    re.compile(r"\b((?:OP|ST|EB|PRB|BT|SD|FB|FS|EX|DB|TB|P)\d{0,2}-\d{2,3}[A-Z]?)\b", re.I),  # OP05-119, BT1-111
    re.compile(r"\b(\d{1,3})\s*/\s*(?:[A-Z]{0,3})?\d{1,3}\b"),               # 199/165, TG05/TG30
    re.compile(r"#\s*([A-Z]{0,5}\d{1,4}[A-Z]?)\b", re.I),                    # #199, #SWSH050
    re.compile(r"\b((?:SWSH|SVP|SM|XY|BW)\s?\d{2,3})\b", re.I),              # promos
]


def fold(text):
    """Lowercase, strip accents (Pokémon -> pokemon) and emoji."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.encode("ascii", "ignore").decode().lower()


def extract_number(title):
    for pat in NUMBER_PATTERNS:
        m = pat.search(title)
        if m:
            return m.group(1).replace(" ", "").upper()
    return None


def norm_number(num):
    """'OP05-119' -> 'op05-119', '007' -> '7' so numbers compare cleanly."""
    if not num:
        return None
    num = num.lower()
    if num.isdigit():
        return num.lstrip("0") or "0"
    return num


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", fold(text)) if t not in NOISE]


def build_query(title, game):
    """Short PriceCharting search query: game name + key words + card number."""
    number = extract_number(title)
    text = fold(title)
    if number:
        text = text.replace(number.lower(), " ")
    text = re.sub(r"\b\d{1,3}\s*/\s*\d{1,3}\b", " ", text)
    text = re.sub(r"\b(19|20)\d{2}\b", " ", text)  # years
    hint_words = set(game["pc_hint"].split()) | {"pokemon", "weiss", "schwarz", "dragon", "ball", "one", "piece"}
    words = [t for t in tokens(text) if t not in hint_words and t != "10" and len(t) > 1]
    query = " ".join([game["pc_hint"]] + words[:7] + ([number] if number else []))
    return query, number


def score_product(title, number, game, product):
    """Return (score, confidence) for one PriceCharting product."""
    name = product.get("product-name", "")
    console = product.get("console-name", "")
    if game["pc_hint"] not in fold(console):
        return 0.0, "none"

    title_toks = set(tokens(title)) - {"10"}
    prod_toks = set(tokens(name + " " + console))
    overlap = len(title_toks & prod_toks) / max(1, len(prod_toks))

    num_match = False
    if number:
        name_nums = {norm_number(n) for n in re.findall(r"#\s*([A-Za-z0-9/-]+)", name)}
        name_nums |= {norm_number(n) for n in re.findall(r"[A-Za-z0-9]+-\d+[A-Za-z]*", name)}
        num_match = norm_number(number.split("/")[0]) in name_nums or norm_number(number) in name_nums

    score = overlap + (1.0 if num_match else 0.0)
    title_jp = bool(JAPANESE_RE.search(title))
    console_jp = "japanese" in fold(console)
    if title_jp != console_jp:
        score -= 0.5

    if num_match and overlap >= 0.3 and title_jp == console_jp:
        conf = "high"
    elif (num_match or overlap >= 0.6) and title_jp == console_jp:
        conf = "medium"
    else:
        conf = "low"
    return score, conf


def best_match(title, number, game, products):
    best = None
    for p in products:
        score, conf = score_product(title, number, game, p)
        if conf == "none":
            continue
        if best is None or score > best[0]:
            best = (score, conf, p)
    return best


def pricecharting_search_url(query):
    return "https://www.pricecharting.com/search-products?" + urllib.parse.urlencode(
        {"q": query, "type": "prices"})


def google_url(title):
    return "https://www.google.com/search?" + urllib.parse.urlencode(
        {"q": f"{title} pricecharting"})
