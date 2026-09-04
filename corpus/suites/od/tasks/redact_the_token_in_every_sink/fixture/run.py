"""Replay a captured event batch through every sink and audit what left.

    python run.py

The line shapes are read by the security dashboard. They are a contract.
"""

import json
import sys

from observe import audit, console, errors, logfile, metrics

DATA = "data/events.json"

SINKS = (
    ("console", console.render),
    ("logfile", logfile.render),
    ("errors", errors.render),
    ("metrics", metrics.render),
)


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        events = json.load(handle)

    print("SINK AUDIT")
    print("events: {}".format(len(events)))
    for name, render in SINKS:
        leaked = 0
        for event in events:
            rendered = render(event)
            if rendered is None:
                continue
            leaked += audit.leaks(rendered)
        print("leaked_{}: {}".format(name, leaked))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
