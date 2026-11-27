"""Read Sailwind markets and calculate trade opportunities."""

import math
import re
import struct
import sys
from dataclasses import dataclass
from time import perf_counter

import pymem

from memhack import read_game_memory
from settings import CONFIG


class Products:
    DATA = CONFIG["products"]
    NAMES = list(DATA.keys())
    PLACEHOLDER_NAMES = {"---", "---2"}


class IslandGroups:
    GROUPS = CONFIG["island_groups"]

    @classmethod
    def get_group(cls, market_name):
        for group, islands in cls.GROUPS.items():
            if market_name in islands:
                return group
        return None


class Product:
    """Represents a product and its pricing/supply calculations."""

    def __init__(self, name, supply_address, pm, limit):
        self.name = name
        self.supply_address = supply_address
        self.pm = pm
        self.limit = limit
        self.volume, self.weight, self.raw_price = Products.DATA[name]
        self.update_product()

    def update_product(self, conversion_rate=311):
        self.supply = read_game_memory(self.pm, self.supply_address, "float")
        self.amnt = max(0, math.floor(self.supply - self.limit + 1))
        self.base_price = self.raw_price * conversion_rate
        self.sell_price = self.calc_sell_price(self.supply)
        self.buy_price = self.calc_buy_price(self.supply)

    def calc_sell_price(self, supply):
        V = self.base_price
        coeff = 0.38 if supply > 0.5 else -1.68
        price = (coeff * V / 10000) * (supply**2) - (abs(coeff) * V / 50) * supply + V
        return math.ceil(price)

    def calc_buy_price(self, supply):
        return math.ceil(self.calc_sell_price(supply) * 1.023)

    def calculate_buy_mult(self, quantity):
        return sum(self.calc_buy_price(self.supply - i) for i in range(quantity))

    def calculate_sell_mult(self, quantity):
        total = sum(
            math.ceil(self.calc_sell_price(self.supply + i)) for i in range(quantity)
        )
        return total

    def max_quantity(self, player, quantity_type="principal"):
        if quantity_type == "mass":
            return math.floor(player.mass_limit / self.weight)
        elif quantity_type == "volume":
            return math.floor(player.volume_limit / self.volume)
        elif quantity_type == "principal":
            i, total_cost = 0, 0
            while i < self.amnt:
                cost = self.calc_buy_price(self.supply - i)
                total_cost += cost
                if total_cost > player.principal:
                    break
                i += 1
            return i

    def max_quantity_mass(self, player):
        return self.max_quantity(player, "mass")

    def max_quantity_volume(self, player):
        return self.max_quantity(player, "volume")

    def max_quantity_principal(self, player):
        return self.max_quantity(player, "principal")


class Market:
    """Represents a market in the game."""

    def __init__(self, pm, base):
        self.pm = pm
        self.base = base
        self.name = self._get_market_name()
        self.index = read_game_memory(pm, pm.read_longlong(base + 0x38) + 0x58, "int")
        self.limit = read_game_memory(pm, base + 0x4C, "float")
        self.products = self._init_products()

    def _get_market_name(self):
        try:
            addr_ptr = self.pm.read_longlong(self.base + 0x38)
            addr = self.pm.read_longlong(addr_ptr + 0x18)
            length = struct.unpack("<I", self.pm.read_bytes(addr + 0x10, 4))[0]
            raw = self.pm.read_bytes(addr + 0x14, length * 2)
            return raw[::2][:length].decode("utf-8", errors="ignore")
        except Exception:
            return "Unknown Market"

    def _init_products(self):
        base_addr = self.pm.read_longlong(self.base + 0x20) + 0x24
        # Enumerate the game's slots before skipping placeholders to preserve offsets.
        return [
            Product(name, base_addr + i * 4, self.pm, self.limit)
            for i, name in enumerate(Products.NAMES)
            if name not in Products.PLACEHOLDER_NAMES
        ]

    def update_products(self, conversion_rate):
        for product in self.products:
            product.update_product(conversion_rate)


@dataclass
class ScanResult:
    addresses: list[int]
    region_query_seconds: float
    memory_read_seconds: float
    signature_match_seconds: float


def scan_market_addresses(handle):
    pattern = re.compile(
        rb"..\x00\x00\x80\x3F\x00\x00.\x42.\x00\x00\x00\x6F\x12\x83\x3A\x00\x00\x80\x3F",
        re.DOTALL,
    )
    # Search for the fixed bytes after the two leading wildcards, then verify the signature.
    anchor = b"\x00\x00\x80\x3f\x00\x00"
    protection = pymem.ressources.structure.MEMORY_PROTECTION
    readable = {
        protection.PAGE_EXECUTE,
        protection.PAGE_EXECUTE_READ,
        protection.PAGE_EXECUTE_READWRITE,
        protection.PAGE_READWRITE,
        protection.PAGE_READONLY,
    }
    committed = pymem.ressources.structure.MEMORY_STATE.MEM_COMMIT
    address = 0
    address_limit = 0x7FFFFFFF0000 if sys.maxsize > 2**32 else 0x7FFF0000
    matches = []
    query_seconds = read_seconds = match_seconds = 0.0
    while address < address_limit:
        started_at = perf_counter()
        region = pymem.memory.virtual_query(handle, address)
        query_seconds += perf_counter() - started_at
        next_address = region.BaseAddress + region.RegionSize
        if region.state == committed and region.protect in readable:
            started_at = perf_counter()
            data = pymem.memory.read_bytes(handle, address, next_address - address)
            read_seconds += perf_counter() - started_at
            started_at = perf_counter()
            anchor_position = data.find(anchor, 2)
            while anchor_position != -1:
                match = pattern.match(data, anchor_position - 2)
                if match:
                    matches.append(address + match.start())
                    anchor_position = data.find(anchor, match.end() + 2)
                else:
                    anchor_position = data.find(anchor, anchor_position + 1)
            match_seconds += perf_counter() - started_at
        address = next_address
    return ScanResult(matches, query_seconds, read_seconds, match_seconds)


def calculate_trade_metrics(start_market, end_market, start_product, player):
    end_product = next(
        (p for p in end_market.products if p.name == start_product.name), None
    )
    if end_product is None:
        return None
    max_qty = min(
        start_product.max_quantity(player, "principal"),
        start_product.max_quantity(player, "mass"),
        start_product.max_quantity(player, "volume"),
        math.floor((abs(start_product.supply - end_product.supply) / 2)),
    )
    if max_qty == 0:
        return None
    total_buy_price = start_product.calculate_buy_mult(max_qty)
    total_sell_price = end_product.calculate_sell_mult(max_qty)
    profit = total_sell_price - total_buy_price
    profit_per_pound = (
        profit / (start_product.weight * max_qty) if start_product.weight else 0
    )
    profit_per_item = profit / max_qty
    return {
        "Start Market": start_market.name,
        "End Market": end_market.name,
        "Product": start_product.name,
        "Qnty": f"{max_qty}/{start_product.amnt}",
        "$_Buy": total_buy_price,
        "$_Sell": total_sell_price,
        "$Profit": profit,
        "$/Pound": round(profit_per_pound, 1),
        "$/Item": round(profit_per_item, 1),
    }


def generate_trade_routes(start_groups, end_groups, player, markets, origin_port=None):
    trade_routes = []
    if origin_port is None:
        start_markets = [
            m for m in markets if IslandGroups.get_group(m.name) in start_groups
        ]
    else:
        start_markets = [m for m in markets if m.name == origin_port]
    end_markets = [m for m in markets if IslandGroups.get_group(m.name) in end_groups]
    for start_market in start_markets:
        for end_market in end_markets:
            if start_market is end_market:
                continue
            for product in start_market.products:
                metrics = calculate_trade_metrics(
                    start_market, end_market, product, player
                )
                if metrics and metrics["$Profit"] > player.min_profit:
                    trade_routes.append(metrics)
    return trade_routes
