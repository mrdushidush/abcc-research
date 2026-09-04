"""Replay yesterday's failures through the retry scheduler.

    python run.py

The line shapes are read by the reliability dashboard. They are a contract.
"""

import json
import sys

from retryd import budget as budget_mod, report, scheduler

DATA = "data/failures.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        failures = json.load(handle)

    budget = budget_mod.Budget(min(f["ts"] for f in failures))
    retried, dropped = scheduler.run(budget, failures)
    rate = report.check(retried, dropped)

    print("RETRY RUN")
    print("failures: {}".format(len(failures)))
    print("retried: {}".format(len(retried)))
    print("dropped_no_budget: {}".format(len(dropped)))
    print("windows_used: {}".format(budget.windows_used()))
    print("retry_rate_pct: {}".format(int(rate * 100)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
