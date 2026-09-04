"""Run the nightly export and audit it.

    python run.py

The line shapes are read by the loader's pre-flight. They are a contract.
"""

import json
import sys

from expo import audit, paging, writer

DATA = "data/rows.json"


def main(argv):
    with open(DATA, encoding="utf-8") as handle:
        rows = json.load(handle)

    pages = paging.pages(rows)
    sink = writer.write_all(writer.Sink(), pages)
    written = audit.check(rows, sink)

    print("EXPORT RUN")
    print("rows: {}".format(len(rows)))
    print("pages: {}".format(len(sink.pages)))
    print("rows_written: {}".format(written))
    print("last_page_rows: {}".format(len(sink.pages[-1]) if sink.pages else 0))
    print("amount_written: {}".format(sum(r["amount_cents"] for r in sink.rows())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
