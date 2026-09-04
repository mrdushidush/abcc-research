"""Compute this batch of cancellation refunds.

    python run.py

The line shapes are read by the refunds run. They are a contract.
"""

import sys

from subs import ledger, prorate

DATA = "data/cancellations.json"


def main(argv):
    records = ledger.load(DATA)
    refunds = {r["id"]: prorate.refund_cents(r) for r in records}

    print("PRORATE RUN")
    print("cancellations: {}".format(len(records)))
    for ident in ("x-1", "x-2", "x-3", "x-4"):
        print("{}_refund_cents: {}".format(ident.replace("-", ""), refunds[ident]))
    print("refund_total_cents: {}".format(sum(refunds.values())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
