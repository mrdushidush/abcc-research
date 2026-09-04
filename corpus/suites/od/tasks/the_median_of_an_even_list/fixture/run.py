"""The monthly cohort report.

    python run.py

The line shapes are read by the finance reconciliation. They are a contract.
"""

import json
import sys

from cohort import group, stats

DATA = "data/orders.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        orders = json.load(handle)

    amounts = [o["amount_cents"] for o in orders]
    regions = group.by_region(orders)

    print("MEDIAN RUN")
    print("orders: {}".format(len(orders)))
    print("median_all_cents: {}".format(stats.median(amounts)))
    for region in sorted(regions):
        print("median_{}_cents: {}".format(region, stats.median(regions[region])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
