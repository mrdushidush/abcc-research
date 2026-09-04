"""The product record and the index everything looks up in."""

import json


class Product:
    def __init__(self, raw):
        self.sku = raw["sku"]
        self.name = raw["name"]
        self.price_cents = int(raw["price_cents"])
        self.on_hand = int(raw["on_hand"])


def load(path):
    with open(path, encoding="utf-8") as handle:
        return {raw["sku"]: Product(raw) for raw in json.load(handle)}
