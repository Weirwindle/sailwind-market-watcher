import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

import market
from settings import PLAYER_SETTINGS, load_player_settings, save_player_settings


class PricingTests(unittest.TestCase):
    def product(self, supply, limit=10):
        with patch("market.read_game_memory", return_value=supply):
            product = market.Product("Goods", 0, None, limit)
            product.update_product(34.22)
        return product

    def test_stock_and_prices_for_synthetic_goods_supply(self):
        # Supply 30 and limit 10 are synthetic inputs, not a captured 0.41 market.
        goods = self.product(30)
        self.assertEqual(goods.amnt, 21)
        self.assertEqual(goods.calculate_buy_mult(1), 193)
        self.assertEqual(goods.calculate_sell_mult(1), 188)

    def test_unavailable_stock_cannot_be_purchased(self):
        goods = self.product(5)
        self.assertEqual(goods.amnt, 0)
        self.assertEqual(goods.max_quantity(SimpleNamespace(principal=10000)), 0)

    def test_departure_and_destination_filters(self):
        origin = SimpleNamespace(name="Gold Rock City", products=[self.product(30)])
        other = SimpleNamespace(name="Oasis", products=[self.product(30)])
        destination = SimpleNamespace(name="Neverdin", products=[self.product(0)])
        player = SimpleNamespace(
            principal=1300, min_profit=0, mass_limit=4000, volume_limit=120
        )
        group = market.IslandGroups.get_group(destination.name)
        markets = [origin, other, destination]
        routes = market.generate_trade_routes([], [group], player, markets, origin.name)
        self.assertEqual(
            [(route["Start Market"], route["End Market"]) for route in routes],
            [(origin.name, destination.name)],
        )
        self.assertEqual(
            market.generate_trade_routes([], [], player, markets, origin.name), []
        )


class ScannerTests(unittest.TestCase):
    def test_placeholder_slots_are_skipped_without_shifting_products(self):
        pm = SimpleNamespace(read_longlong=lambda address: 100)
        scanned_market = SimpleNamespace(pm=pm, base=0, limit=10)
        with patch("market.read_game_memory", return_value=30):
            products = market.Market._init_products(scanned_market)

        names = market.Products.NAMES
        self.assertNotIn("---", [product.name for product in products])
        self.assertNotIn("---2", [product.name for product in products])
        for product in products:
            self.assertEqual(
                product.supply_address, 100 + 0x24 + names.index(product.name) * 4
            )

    def test_anchored_search_matches_original_signature(self):
        signature = rb"..\x00\x00\x80\x3F\x00\x00.\x42.\x00\x00\x00\x6F\x12\x83\x3A\x00\x00\x80\x3F"
        match_bytes = b"\n\0\0\0\x80\x3f\0\0\n\x42\0\0\0\0\x6f\x12\x83\x3a\0\0\x80\x3f"
        data = match_bytes * 2 + match_bytes[:-1] + b"\0" + match_bytes
        memory = market.pymem.ressources.structure
        limit = 0x7FFFFFFF0000 if sys.maxsize > 2**32 else 0x7FFF0000
        regions = [
            SimpleNamespace(
                BaseAddress=0,
                RegionSize=len(data),
                state=memory.MEMORY_STATE.MEM_COMMIT,
                protect=memory.MEMORY_PROTECTION.PAGE_READWRITE,
            ),
            SimpleNamespace(
                BaseAddress=len(data), RegionSize=limit - len(data), state=0, protect=0
            ),
        ]
        with (
            patch("market.pymem.memory.virtual_query", side_effect=regions),
            patch("market.pymem.memory.read_bytes", return_value=data) as read,
        ):
            result = market.scan_market_addresses(None)
        self.assertEqual(
            result.addresses,
            [m.start() for m in re.finditer(signature, data, re.DOTALL)],
        )
        self.assertEqual(len(result.addresses), 3)
        read.assert_called_once_with(None, 0, len(data))


class SettingsTests(unittest.TestCase):
    def test_saved_settings_round_trip_and_corrupt_file_fallback(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "watcher" / "player-settings.json"
            self.assertEqual(load_player_settings(path), PLAYER_SETTINGS)
            saved = {**PLAYER_SETTINGS, "mass_limit": 1000, "volume_limit": 40}
            save_player_settings(path, saved)
            self.assertEqual(load_player_settings(path), saved)
            path.write_text("{", encoding="utf-8")
            self.assertEqual(load_player_settings(path), PLAYER_SETTINGS)
