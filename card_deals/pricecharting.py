"""PriceCharting API lookups (optional; needs a paid PriceCharting subscription).

For trading cards PriceCharting reuses its video-game field names:
  manual-only-price = PSA 10, graded-price = PSA 9, loose-price = ungraded.
Prices come back in pennies.
Docs: https://www.pricecharting.com/api-documentation
"""

import json
import os
import time
import urllib.parse

from . import config
from .http import request_json
from .matching import best_match, build_query

API = "https://www.pricecharting.com/api"


def _cents(v):
    try:
        return round(int(v) / 100, 2) if v else None
    except (TypeError, ValueError):
        return None


class PriceCharting:
    def __init__(self, token, cache_path=config.PC_CACHE_PATH):
        self.token = token
        self.cache_path = cache_path
        self.cache = {}
        self.calls = 0
        self.ok = 0
        self.failed = 0
        self.consecutive_failures = 0
        self.disabled_reason = None
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    self.cache = json.load(f)
            except (OSError, ValueError):
                self.cache = {}

    def save(self):
        os.makedirs(os.path.dirname(self.cache_path) or ".", exist_ok=True)
        cutoff = time.time() - config.PC_CACHE_DAYS * 86400
        fresh = {k: v for k, v in self.cache.items() if v.get("ts", 0) >= cutoff}
        with open(self.cache_path, "w") as f:
            json.dump(fresh, f)

    def _get(self, path, **params):
        time.sleep(1)  # be polite: about one call per second
        self.calls += 1
        params["t"] = self.token
        resp = request_json(f"{API}/{path}?{urllib.parse.urlencode(params)}")
        if resp.get("status") == "error":
            raise RuntimeError(f"PriceCharting error: {resp.get('error-message', resp)}")
        return resp

    def _search(self, query):
        hit = self.cache.get(query)
        if hit and hit.get("ts", 0) >= time.time() - config.PC_CACHE_DAYS * 86400:
            return hit["products"]
        resp = self._get("products", q=query)
        products = resp.get("products") or []
        self.cache[query] = {"ts": time.time(), "products": products}
        return products

    def _prices(self, product):
        if "manual-only-price" not in product:
            key = f"id:{product['id']}"
            hit = self.cache.get(key)
            if hit and hit.get("ts", 0) >= time.time() - config.PC_CACHE_DAYS * 86400:
                product = hit["product"]
            else:
                product = self._get("product", id=product["id"])
                self.cache[key] = {"ts": time.time(), "product": product}
        return {
            "psa10": _cents(product.get("manual-only-price")),
            "psa9": _cents(product.get("graded-price")),
            "ungraded": _cents(product.get("loose-price")),
        }

    MAX_CONSECUTIVE_FAILURES = 5

    def lookup(self, title, game):
        if self.disabled_reason:
            return None
        query, number = build_query(title, game)
        try:
            products = self._search(query)
            if not products and number:
                # Retry with just the game and card number.
                products = self._search(f"{game['pc_hint']} {number}")
            match = best_match(title, number, game, products)
            self.consecutive_failures = 0
            if not match:
                return None
            _, conf, product = match
            info = {
                "name": product.get("product-name"),
                "console": product.get("console-name"),
                "id": product.get("id"),
                "confidence": conf,
                **self._prices(product),
            }
            self.ok += 1
            return info
        except RuntimeError as e:
            self.failed += 1
            self.consecutive_failures += 1
            print(f"  PriceCharting lookup failed for {title!r}: {e}")
            if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                self.disabled_reason = str(e)
                print(f"  Stopping PriceCharting lookups after {self.consecutive_failures} failures in a row.")
            return None

    def status(self):
        return {"matched": self.ok, "failed": self.failed, "error": self.disabled_reason}
