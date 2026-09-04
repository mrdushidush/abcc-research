"""Ingest a batch of barometer readings, calibrate them, and report.

    python run.py

The line shapes are read by the instrument dashboard. They are a contract.
"""

import sys

from baro import calibrate, ingest, report

READINGS = "data/readings.json"
OFFSETS = "data/offsets.json"


def main(argv):
    raw = ingest.readings(READINGS)
    calibrated = calibrate.apply(raw, ingest.offsets(OFFSETS))
    summary = report.summarise(calibrated)

    print("PRESSURE RUN")
    print("readings: {}".format(len(calibrated)))
    print("mean_ckpa: {}".format(summary["mean_ckpa"]))
    print("s2_mean_ckpa: {}".format(summary["sensor_mean"]["s2"]))
    print("below_min: {}".format(len(summary["below"])))
    print("above_max: {}".format(len(summary["above"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
