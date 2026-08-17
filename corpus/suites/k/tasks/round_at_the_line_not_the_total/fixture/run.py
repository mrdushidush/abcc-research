#!/usr/bin/env python3
"""Price a batch of orders and print the receipts, a summary, and the audit.

    python3 run.py data/orders.json
"""

import json
import sys

from billing import audit, invoice, receipt, validate


def main(argv):
    if len(argv) < 2:
        print("usage: run.py <orders.json>", file=sys.stderr)
        return 2

    with open(argv[1], encoding="utf-8") as fh:
        orders = json.load(fh)

    ok, errors = validate.check_all(orders)
    if errors:
        for err in errors:
            print("INVALID ORDER: %s" % err, file=sys.stderr)
        return 1

    invoices = invoice.build_all(orders)

    print(receipt.render_all(invoices))
    print()
    print(receipt.summary(invoices))
    print()
    print(audit.render(audit.audit(invoices)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
