"""Render Ana's August statement four ways and report each total.

    python run.py

The line shapes are read by the reconciliation job. They are a contract.
"""

import sys

from statement import csv_out, html_out, json_out, load, summary

DATA = "data/ledger.json"

RENDERERS = (
    ("csv", csv_out.total),
    ("json", json_out.total),
    ("html", html_out.total),
    ("summary", summary.total),
)


def main(argv):
    transactions = load.transactions(DATA)
    print("STATEMENT TOTALS")
    print("transactions: {}".format(len(transactions)))
    for name, total in RENDERERS:
        print("{}_total: {}".format(name, total(transactions)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
