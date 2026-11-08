"""All the knobs in one place. Edit these to change what the tool looks for."""

import os

# One eBay search per game. `pc_hint` is matched against PriceCharting's
# "console" name (e.g. "Pokemon Scarlet & Violet 151") to keep matches in the
# right game.
GAMES = [
    {"key": "pokemon", "label": "Pokémon", "query": "pokemon psa 10", "pc_hint": "pokemon"},
    {"key": "onepiece", "label": "One Piece", "query": "one piece psa 10", "pc_hint": "one piece"},
    {"key": "dragonball", "label": "Dragon Ball", "query": "dragon ball psa 10", "pc_hint": "dragon ball"},
    {"key": "weiss", "label": "Weiss Schwarz", "query": "weiss schwarz psa 10", "pc_hint": "weiss"},
]

MIN_PRICE = 200            # USD, minimum current bid
HOURS_AHEAD = 13           # only auctions ending within this many hours
DEAL_THRESHOLD = 0.10      # a "deal" = current bid at least 10% under PSA 10 market
REFRESH_HOURS = 12         # shown on the page; the real schedule is in .github/workflows/deals.yml

# eBay "CCG Individual Cards" category. Set EBAY_CATEGORY_ID="" to search all categories.
EBAY_CATEGORY_ID = os.environ.get("EBAY_CATEGORY_ID", "183454")
# Optional eBay aspect filter, e.g. "categoryId:183454,Grade:{10}". Off by default;
# every title is checked for "PSA 10" instead, which is more reliable.
EBAY_ASPECT_FILTER = os.environ.get("EBAY_ASPECT_FILTER", "")
# Optional US ZIP code so eBay returns shipping costs to you.
SHIP_TO_ZIP = os.environ.get("SHIP_TO_ZIP", "")
MAX_RESULTS_PER_GAME = 1000

EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "")
PRICECHARTING_TOKEN = os.environ.get("PRICECHARTING_TOKEN", "")

PC_CACHE_PATH = os.environ.get("PC_CACHE_PATH", "data/pc_cache.json")
PC_CACHE_DAYS = 3          # reuse a PriceCharting lookup for this many days
