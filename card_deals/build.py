"""Build the deals web page.

    python -m card_deals.build --out site/index.html          # real data
    python -m card_deals.build --out site/index.html --demo   # sample data, no keys needed
"""

import argparse
import json
import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config
from .matching import build_query, extract_number, google_url, pricecharting_search_url

TEMPLATE = Path(__file__).with_name("template.html")


def enrich(item, game, pc=None):
    query, _ = build_query(item["title"], game)
    item["card_number"] = extract_number(item["title"])
    item["pc_search_url"] = pricecharting_search_url(query.replace(game["pc_hint"], game["label"], 1))
    item["google_url"] = google_url(item["title"])
    item["pc"] = pc.lookup(item["title"], game) if pc else None
    return item


def fetch_live():
    from . import ebay
    from .pricecharting import PriceCharting

    if not (config.EBAY_CLIENT_ID and config.EBAY_CLIENT_SECRET):
        sys.exit("Missing EBAY_CLIENT_ID / EBAY_CLIENT_SECRET. See README.md, or use --demo.")
    token = ebay.get_token(config.EBAY_CLIENT_ID, config.EBAY_CLIENT_SECRET)
    pc = PriceCharting(config.PRICECHARTING_TOKEN) if config.PRICECHARTING_TOKEN else None

    listings, seen = [], set()
    for game in config.GAMES:
        items = ebay.search_game(token, game)
        print(f"{game['label']}: {len(items)} PSA 10 auctions")
        for item in items:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            listings.append(enrich(item, game, pc))
    pc_status = None
    if pc:
        pc.save()
        pc_status = pc.status()
        print(f"PriceCharting API calls this run: {pc.calls}; matched {pc_status['matched']}, failed {pc_status['failed']}")
        if pc_status["error"]:
            print(f"::warning::PriceCharting lookups stopped: {pc_status['error']}")
    return listings, bool(pc), pc_status


def demo_listings():
    """Made-up sample data so the page can be previewed without API keys."""
    now = datetime.now(timezone.utc)
    games = {g["key"]: g for g in config.GAMES}
    samples = [
        ("pokemon", "Charizard ex 199/165 Pokemon 151 Special Illustration Rare PSA 10", 0.6, 620, 14, 9.5,
         {"name": "Charizard ex #199", "console": "Pokemon Scarlet & Violet 151", "confidence": "high", "psa10": 780, "psa9": 310, "ungraded": 105}),
        ("pokemon", "Umbreon VMAX 215/203 Evolving Skies Alt Art PSA 10 GEM MINT", 2.2, 1450, 22, 0,
         {"name": "Umbreon VMAX #215", "console": "Pokemon Evolving Skies", "confidence": "high", "psa10": 1550, "psa9": 760, "ungraded": 520}),
        ("pokemon", "Pikachu with Grey Felt Hat 085 Van Gogh Promo PSA 10", 5.1, 410, 9, 5,
         {"name": "Pikachu with Grey Felt Hat #085", "console": "Pokemon Promo", "confidence": "medium", "psa10": 520, "psa9": 230, "ungraded": 95}),
        ("pokemon", "Japanese Mew ex 347/190 Shiny Treasure PSA 10", 8.9, 230, 3, 6,
         {"name": "Mew ex #347", "console": "Pokemon Japanese Shiny Treasure ex", "confidence": "high", "psa10": 240, "psa9": 120, "ungraded": 60}),
        ("pokemon", "Lugia V Alt Art 186/195 Silver Tempest PSA 10 🔥🔥", 11.5, 380, 7, 4.99,
         {"name": "Lugia V #186", "console": "Pokemon Silver Tempest", "confidence": "high", "psa10": 470, "psa9": 210, "ungraded": 140}),
        ("onepiece", "Monkey D. Luffy OP05-119 Manga Alt Art One Piece PSA 10", 1.3, 2100, 31, 0,
         {"name": "Monkey.D.Luffy [Manga] OP05-119", "console": "One Piece Awakening of the New Era", "confidence": "high", "psa10": 2600, "psa9": 1500, "ungraded": 1100}),
        ("onepiece", "Shanks OP01-120 Parallel Romance Dawn One Piece PSA 10", 6.4, 330, 5, 8,
         {"name": "Shanks [Alternate Art] OP01-120", "console": "One Piece Romance Dawn", "confidence": "medium", "psa10": 340, "psa9": 180, "ungraded": 120}),
        ("dragonball", "Son Goku BT1-111 SCR Galactic Battle Dragon Ball Super PSA 10", 3.7, 260, 6, 5,
         {"name": "Son Goku, The Awakened Power BT1-111", "console": "Dragon Ball Super Galactic Battle", "confidence": "low", "psa10": 400, "psa9": 150, "ungraded": 70}),
        ("dragonball", "Dragon Ball Z Goku Carddass Prism 1991 PSA 10", 9.8, 290, 4, 12, None),
        ("weiss", "Weiss Schwarz Asuna SAO/S20-001SP Signed PSA 10", 4.4, 520, 8, 15, None),
        ("weiss", "Weiss Schwarz Hololive Pekora HOL/W91-001SSP PSA 10", 12.4, 210, 2, 6, None),
    ]
    listings = []
    for i, (gkey, title, hours, bid, bids, ship, pc) in enumerate(samples):
        item = {
            "id": f"demo-{i}",
            "game": gkey,
            "title": title,
            "url": "https://www.ebay.com/sch/i.html?" + urllib.parse.urlencode({"_nkw": title}),
            "image": None,
            "current_bid": float(bid),
            "currency": "USD",
            "bid_count": bids,
            "shipping": float(ship),
            "end_time": (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "seller": "demo_seller",
            "seller_feedback": "99.8",
            "seller_score": 1234,
        }
        enrich(item, games[gkey])
        item["pc"] = pc
        listings.append(item)
    return listings


def render(listings, has_pricecharting, demo, out_path, pc_status=None):
    now = datetime.now(timezone.utc)
    payload = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "next_refresh": (now + timedelta(hours=config.REFRESH_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hours_ahead": config.HOURS_AHEAD,
        "min_price": config.MIN_PRICE,
        "deal_threshold": config.DEAL_THRESHOLD,
        "has_pricecharting": has_pricecharting,
        "pc_status": pc_status,
        "demo": demo,
        "games": [{"key": g["key"], "label": g["label"]} for g in config.GAMES],
        "listings": sorted(listings, key=lambda x: x["end_time"] or ""),
    }
    data = json.dumps(payload).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", data)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"Wrote {out_path} with {len(listings)} listings")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="site/index.html")
    ap.add_argument("--demo", action="store_true", help="use sample data (no API keys needed)")
    args = ap.parse_args()
    if args.demo:
        render(demo_listings(), True, True, args.out)
    else:
        listings, has_pc, pc_status = fetch_live()
        render(listings, has_pc, False, args.out, pc_status)


if __name__ == "__main__":
    main()
