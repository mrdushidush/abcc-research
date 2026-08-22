"""Arm E — the author's report AND the diff, in one prompt.

Run after `independence.py`, because it only has a question once arm B is known.
If E tracks A, a completion report is harmless decoration and the pipeline may
carry it. If E tracks B, the report is not merely insufficient — it is poison,
and the Judge's prompt has to exclude it by construction.
"""

import json
import sys

import common as C
import independence as I


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    rows = []
    for a in C.ARTIFACTS:
        I.run("E-both", a, n, C.CHAMPION, rows)
    (C.HERE / "armE-results.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    I.summarise(rows)


if __name__ == "__main__":
    main()
