#!/usr/bin/env python3
"""Load a job snapshot and print the operational report.

    python3 run.py data/jobs.json

`now` is taken from the snapshot rather than the clock, so the report is
reproducible.
"""

import json
import sys

from jobs import charges, model, notify, retry, sla, summary, validate


def main(argv):
    if len(argv) < 2:
        print("usage: run.py <jobs.json>", file=sys.stderr)
        return 2

    with open(argv[1], encoding="utf-8") as fh:
        snapshot = json.load(fh)

    records = snapshot["jobs"]
    now = snapshot["now"]

    ok, errors = validate.check_all(records)
    if errors:
        for err in errors:
            print("INVALID RECORD: %s" % err, file=sys.stderr)
        return 1

    jobs = model.load_all(records)

    print("JOBS %d at now=%d" % (len(jobs), now))
    print(summary.report(jobs))
    print(sla.report(jobs, now))
    print(charges.report(jobs))
    print(retry.report(jobs))
    print(notify.report(jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
