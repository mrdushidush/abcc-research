"""Quote today's parcels.

    python run.py

The line shapes are read by the carrier reconciliation. They are a contract.
"""

import json
import sys

from shiprate import quote as quote_mod

DATA = "data/parcels.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        parcels = json.load(handle)

    quotes = quote_mod.quotes(parcels)
    by_id = {q["id"]: q for q in quotes}

    print("SHIPPING RUN")
    print("parcels: {}".format(len(quotes)))
    print("billable_total_dg: {}".format(sum(q["billable_dg"] for q in quotes)))
    print("charged_total_cents: {}".format(sum(q["cents"] for q in quotes)))
    print("p1_billable_dg: {}".format(by_id["p-1"]["billable_dg"]))
    print("p2_billable_dg: {}".format(by_id["p-2"]["billable_dg"]))
    print("p5_billable_dg: {}".format(by_id["p-5"]["billable_dg"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
