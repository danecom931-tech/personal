import os
import tempfile
import unittest
from unittest import mock

from card_deals.config import GAMES
from card_deals.http import DEFAULT_HEADERS
from card_deals.pricecharting import PriceCharting

POKEMON = GAMES[0]


class PriceChartingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pc = PriceCharting("tok", cache_path=os.path.join(self.tmp, "c.json"))

    def test_user_agent_is_not_python_default(self):
        self.assertNotIn("Python-urllib", DEFAULT_HEADERS["User-Agent"])

    def test_match_with_prices(self):
        products = [{"id": "1", "product-name": "Charizard ex #199", "console-name": "Pokemon Scarlet & Violet 151",
                     "manual-only-price": 78000, "graded-price": 31000, "loose-price": 10500}]
        with mock.patch("card_deals.pricecharting.request_json", return_value={"status": "success", "products": products}), \
             mock.patch("time.sleep"):
            info = self.pc.lookup("Charizard ex 199/165 Pokemon 151 PSA 10", POKEMON)
        self.assertEqual(info["psa10"], 780.0)
        self.assertEqual(info["confidence"], "high")
        self.assertEqual(self.pc.status(), {"matched": 1, "failed": 0, "error": None})

    def test_stops_after_repeated_failures(self):
        err = RuntimeError("HTTP 403: error code: 1010")
        with mock.patch("card_deals.pricecharting.request_json", side_effect=err) as rj, mock.patch("time.sleep"):
            for i in range(20):
                self.assertIsNone(self.pc.lookup(f"Card {i} 1{i}/165 PSA 10", POKEMON))
        self.assertEqual(rj.call_count, PriceCharting.MAX_CONSECUTIVE_FAILURES)
        self.assertIn("1010", self.pc.status()["error"])

    def test_error_status_counts_as_failure(self):
        with mock.patch("card_deals.pricecharting.request_json",
                        return_value={"status": "error", "error-message": "Invalid token"}), mock.patch("time.sleep"):
            self.assertIsNone(self.pc.lookup("Charizard 4/102 PSA 10", POKEMON))
        self.assertEqual(self.pc.status()["failed"], 1)


if __name__ == "__main__":
    unittest.main()
