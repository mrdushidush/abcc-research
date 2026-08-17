#!/usr/bin/env python3
"""Entry point for the telemetry roll-up.

Reads a JSONL sample file, runs it through the pipeline, and prints a report.

    python3 run.py data/samples.jsonl
"""

import json
import sys

from pipeline import calibration, config, ingest, report, stats, windowing


def main(argv):
    if len(argv) < 2:
        print("usage: run.py <samples.jsonl>", file=sys.stderr)
        return 2

    path = argv[1]
    with open(path, encoding="utf-8") as fh:
        raw = [json.loads(line) for line in fh if line.strip()]

    settings = config.load()
    cal = calibration.load_table(settings)

    accepted = ingest.accept(raw, settings)
    calibrated = calibration.apply(accepted, cal)
    windows = windowing.split(calibrated, settings)
    summary = stats.summarise(windows, settings)

    print(report.render(summary, settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
