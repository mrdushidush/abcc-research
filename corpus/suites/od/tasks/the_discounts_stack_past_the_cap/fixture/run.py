"""Price today's discounted orders.

    python run.py

The line shapes are read by the margin report. They are a contract.
"""

import sys

from checkout import orders as orders_mod, pricing

DATA = "data/orders.json"


def main(argv):
    orders = orders_mod.load(DATA)
    payable = {o["id"]: pricing.payable(o["subtotal_cents"], o["discounts"]) for o in orders}

    print("DISCOUNT RUN")
    print("orders: {}".format(len(orders)))
    print("o1_cents: {}".format(payable["o-1"]))
    print("o2_cents: {}".format(payable["o-2"]))
    print("o3_cents: {}".format(payable["o-3"]))
    print("o4_cents: {}".format(payable["o-4"]))
    print("payable_total_cents: {}".format(sum(payable.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
