"""Quote the pending orders and report what each registry knew.

    python run.py

The line shapes are read by the finance close. They are a contract.
"""

import json
import sys

from taxq import exemptions, filing, labels, quote, regions

DATA = "data/orders.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        orders = json.load(handle)

    unsupported = [o["id"] for o in orders if not regions.supported(o["region"])]
    present = sorted({o["region"] for o in orders})

    print("TAX QUOTE RUN")
    print("orders: {}".format(len(orders)))
    print("unsupported: {}".format(len(unsupported)))
    print("tax_cents: {}".format(sum(quote.tax_cents(o) for o in orders)))
    print("labelled: {}".format(sum(1 for o in orders if labels.label(o["region"]))))
    print("filings: {}".format(sum(1 for r in present if filing.period(r))))
    print(
        "exempt_lines: {}".format(
            sum(1 for o in orders if exemptions.exempt(o["region"], o["category"]))
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
