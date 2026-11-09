"""eBay Browse API: find PSA 10 auctions ending soon.

Uses eBay's official API (free developer account), not page scraping.
Docs: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
"""

import base64
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import config
from .http import request_json

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

PSA10_RE = re.compile(r"\bPSA\s*[-:]?\s*(?:GEM\s*(?:MT|MINT)\s*)?10\b", re.I)
LOT_RE = re.compile(r"\b(lot|bundle|set of|x\d+|\d+\s*(?:cards|slabs))\b", re.I)


def get_token(client_id, client_secret):
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    })
    resp = request_json(TOKEN_URL, method="POST", data=data, headers={
        "Authorization": f"Basic {creds}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    return resp["access_token"]


def is_single_psa10(title):
    """True if the title says PSA 10 and doesn't look like a multi-card lot."""
    return bool(PSA10_RE.search(title)) and not LOT_RE.search(title)


def _money(obj):
    try:
        return float(obj["value"])
    except (TypeError, KeyError, ValueError):
        return None


def parse_item(raw, game_key):
    bid = _money(raw.get("currentBidPrice")) or _money(raw.get("price"))
    shipping = None
    for opt in raw.get("shippingOptions") or []:
        shipping = _money(opt.get("shippingCost"))
        if shipping is not None:
            break
    seller = raw.get("seller") or {}
    return {
        "id": raw.get("itemId"),
        "game": game_key,
        "title": raw.get("title", ""),
        "url": raw.get("itemWebUrl"),
        "image": (raw.get("image") or {}).get("imageUrl"),
        "current_bid": bid,
        "currency": (raw.get("currentBidPrice") or raw.get("price") or {}).get("currency", "USD"),
        "bid_count": raw.get("bidCount", 0),
        "shipping": shipping,
        "end_time": raw.get("itemEndDate"),
        "seller": seller.get("username"),
        "seller_feedback": seller.get("feedbackPercentage"),
        "seller_score": seller.get("feedbackScore"),
    }


def search_game(token, game, now=None):
    now = now or datetime.now(timezone.utc)
    end_by = (now + timedelta(hours=config.HOURS_AHEAD)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    filters = [
        "buyingOptions:{AUCTION}",
        f"price:[{config.MIN_PRICE}..]",
        "priceCurrency:USD",
        f"itemEndDate:[..{end_by}]",
    ]
    params = {
        "q": game["query"],
        "filter": ",".join(filters),
        "sort": "endingSoonest",
        "limit": "200",
    }
    if config.EBAY_CATEGORY_ID:
        params["category_ids"] = config.EBAY_CATEGORY_ID
    if config.EBAY_ASPECT_FILTER:
        params["aspect_filter"] = config.EBAY_ASPECT_FILTER

    headers = {"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"}
    if config.SHIP_TO_ZIP:
        headers["X-EBAY-C-ENDUSERCTX"] = f"contextualLocation=country%3DUS%2Czip%3D{config.SHIP_TO_ZIP}"

    items, offset = [], 0
    while offset < config.MAX_RESULTS_PER_GAME:
        params["offset"] = str(offset)
        resp = request_json(f"{SEARCH_URL}?{urllib.parse.urlencode(params)}", headers=headers)
        page = resp.get("itemSummaries") or []
        for raw in page:
            item = parse_item(raw, game["key"])
            if item["current_bid"] is None or not is_single_psa10(item["title"]):
                continue
            items.append(item)
        if not resp.get("next") or not page:
            break
        offset += len(page)
    return items
