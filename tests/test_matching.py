import unittest

from card_deals.config import GAMES
from card_deals.ebay import is_single_psa10, parse_item
from card_deals.matching import best_match, build_query, extract_number

G = {g["key"]: g for g in GAMES}


class TitleTests(unittest.TestCase):
    def test_psa10_detection(self):
        self.assertTrue(is_single_psa10("Charizard ex 199/165 PSA 10 GEM MINT"))
        self.assertTrue(is_single_psa10("Umbreon VMAX PSA GEM MT 10"))
        self.assertFalse(is_single_psa10("Charizard ex PSA 9 MINT"))
        self.assertFalse(is_single_psa10("Charizard PSA 100 pop"))
        self.assertFalse(is_single_psa10("Lot of 3 Pokemon PSA 10 cards"))

    def test_card_numbers(self):
        self.assertEqual(extract_number("Charizard ex 199/165 151 PSA 10"), "199")
        self.assertEqual(extract_number("Luffy OP05-119 Manga PSA 10"), "OP05-119")
        self.assertEqual(extract_number("Goku BT1-111 SCR PSA 10"), "BT1-111")
        self.assertEqual(extract_number("Asuna SAO/S20-001SP PSA 10"), "SAO/S20-001SP")
        self.assertEqual(extract_number("Pikachu #085 Van Gogh PSA 10"), "085")

    def test_query(self):
        q, n = build_query("🔥Pokémon Charizard ex 199/165 151 SIR PSA 10 GEM MINT🔥", G["pokemon"])
        self.assertEqual(n, "199")
        self.assertTrue(q.startswith("pokemon charizard ex"))
        self.assertNotIn("psa", q)
        self.assertTrue(q.endswith("199"))


class MatchTests(unittest.TestCase):
    PRODUCTS = [
        {"id": "1", "product-name": "Charizard ex #199", "console-name": "Pokemon Scarlet & Violet 151"},
        {"id": "2", "product-name": "Charizard ex #6", "console-name": "Pokemon Scarlet & Violet 151"},
        {"id": "3", "product-name": "Charizard ex #199", "console-name": "Pokemon Japanese Scarlet & Violet 151"},
        {"id": "4", "product-name": "Charizard #4", "console-name": "Magic"},
    ]

    def test_picks_number_and_language(self):
        t = "Charizard ex 199/165 Pokemon 151 PSA 10"
        _, conf, p = best_match(t, extract_number(t), G["pokemon"], self.PRODUCTS)
        self.assertEqual(p["id"], "1")
        self.assertEqual(conf, "high")

    def test_japanese(self):
        t = "Japanese Charizard ex 199/165 Pokemon 151 PSA 10"
        _, _, p = best_match(t, extract_number(t), G["pokemon"], self.PRODUCTS)
        self.assertEqual(p["id"], "3")

    def test_wrong_game_ignored(self):
        self.assertIsNone(best_match("Charizard PSA 10", None, G["onepiece"], self.PRODUCTS))


class ParseTests(unittest.TestCase):
    def test_parse_auction(self):
        raw = {
            "itemId": "v1|123|0", "title": "X PSA 10", "itemWebUrl": "https://ebay.com/itm/123",
            "currentBidPrice": {"value": "250.00", "currency": "USD"}, "bidCount": 4,
            "shippingOptions": [{"shippingCost": {"value": "5.00"}}],
            "itemEndDate": "2026-11-09T01:00:00.000Z", "seller": {"username": "s", "feedbackPercentage": "99.9"},
        }
        it = parse_item(raw, "pokemon")
        self.assertEqual(it["current_bid"], 250.0)
        self.assertEqual(it["shipping"], 5.0)
        self.assertEqual(it["bid_count"], 4)


if __name__ == "__main__":
    unittest.main()
