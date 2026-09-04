"""Total yesterday's orders and reconcile them against the provider.

    python run.py

The line shapes are read by the settlement import. They are a contract.
"""

import json
import sys

from till import lines, reconcile

DATA = "data/orders.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        orders = json.load(handle)

    reconciled = reconcile.check(orders)

    by_currency = {}
    for order in orders:
        by_currency.setdefault(order["currency"], 0)
        by_currency[order["currency"]] += lines.order_total(order)

    print("RECONCILE RUN")
    print("orders: {}".format(len(orders)))
    print("reconciled: {}".format(reconciled))
    for currency in sorted(by_currency):
        print("total_{}_minor: {}".format(currency.lower(), by_currency[currency]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
