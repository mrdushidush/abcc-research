"""The latency percentile report.

    python run.py

The line shapes are read by the SLO dashboard. They are a contract.
"""

import sys

from latency import percentiles, windows

DATA = "data/windows.json"


def main(argv):
    data = windows.load(DATA)
    print("LATENCY RUN")
    print("windows: {}".format(len(data)))
    for name in sorted(data):
        summary = percentiles.summary(data[name])
        print("{}_p50_ms: {}".format(name, summary["p50"]))
        print("{}_p95_ms: {}".format(name, summary["p95"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
