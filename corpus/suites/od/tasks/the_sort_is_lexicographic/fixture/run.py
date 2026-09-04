"""Build the ordered ledger file and pre-flight it.

    python run.py

The line shapes are read by the reader's pre-flight. They are a contract.
"""

import json
import sys

from ledgerout import sequence, writer

DATA = "data/records.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        records = json.load(handle)

    checked = sequence.check(records)
    emitted = writer.emit(records)
    trail = writer.running_balance(records)

    print("LEDGER RUN")
    print("records: {}".format(checked))
    print("first_written: {}".format(emitted[0]))
    print("second_written: {}".format(emitted[1]))
    print("last_written: {}".format(emitted[-1]))
    print("balance_after_two: {}".format(trail[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
