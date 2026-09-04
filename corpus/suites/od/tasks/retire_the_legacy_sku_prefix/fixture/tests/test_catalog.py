"""Visible tests.

⚠ Every SKU in this file is canonical, so nothing here needs folding and
nothing here notices a reader that does not fold. `normalize` itself is well
covered — in isolation.
"""

from catalog import cart, export, inventory, model, search, skus


def index():
    return model.load("data/products.json")


def test_normalize_strips_the_legacy_prefix():
    assert skus.normalize("OLD-1101") == "1101"
    assert skus.normalize("old-1101") == "1101"
    assert skus.normalize(" 1101 ") == "1101"
    assert skus.normalize("1101") == "1101"
    assert skus.normalize(None) is None


def test_search_finds_a_canonical_sku():
    assert search.hits(index(), ["1101", "2202"]) == ["1101", "2202"]


def test_search_misses_an_unknown_sku():
    assert search.hits(index(), ["9999"]) == []


def test_cart_prices_a_line():
    assert cart.price_line(index(), {"sku": "1101", "qty": 2}) == 2900


def test_inventory_applies_a_delta():
    idx = index()
    assert inventory.apply(idx, [{"sku": "3303", "delta": -2}]) == ["3303"]
    assert idx["3303"].on_hand == 38


def test_export_has_one_row_per_product():
    rows = export.rows(index())
    assert len(rows) == 6
    assert rows[0]["sku"] == "1101"
