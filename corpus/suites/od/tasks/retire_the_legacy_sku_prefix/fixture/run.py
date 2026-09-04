"""Nightly catalog reconciliation.

    python run.py

Replays yesterday's traffic against the catalog and reports what resolved.
The line shapes are read by the ops dashboard.
"""

import json
import sys

from catalog import cart, export, inventory, model, search

PRODUCTS = "data/products.json"
TRAFFIC = "data/traffic.json"


def main(argv):
    index = model.load(PRODUCTS)
    with open(TRAFFIC, encoding="utf-8") as handle:
        traffic = json.load(handle)

    print("CATALOG RECONCILIATION")
    print("products: {}".format(len(index)))
    print("search_hits: {}".format(len(search.hits(index, traffic["searches"]))))
    print("cart_priced: {}".format(len(cart.priced(index, traffic["cart"]))))
    print("inventory_applied: {}".format(len(inventory.apply(index, traffic["adjustments"]))))
    print("export_rows: {}".format(len(export.rows(index))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
