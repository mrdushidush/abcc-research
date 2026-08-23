#!/usr/bin/env python3
"""W6 item 5 — F307's table, extended to all five Q56 languages.

Item 4 ran the ladder over the rust and python halves of Q56 (377 cells, F307)
and left the node, typescript and shell cells unmeasured because
`instruments.q56_ladder` had no rungs for them. Item 5 added the rungs (see
`../w6-headroom/instruments.py`, the "node / typescript / shell" section) and
re-ran `ladder.py q56`, which is resumable and therefore only measured the 351
new cells.

This prints the same shape F307 used: for each rung, how often it is red on a
tree the suite verifier rejects and how often it is red on one it accepts.

Reads ../w6-headroom/results-q56.json. Writes nothing.
"""

from __future__ import annotations

import collections
import json
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE.parent / "w6-headroom" / "results-q56.json"

ORDER = ["rust", "python", "node", "typescript", "shell"]


def main() -> None:
    rows = json.loads(RESULTS.read_text(encoding="utf-8"))
    by_lang: dict[str, list] = collections.defaultdict(list)
    for r in rows:
        by_lang[r.get("lang", "?")].append(r)

    print(f"{'language':11} {'cells':>6} {'FAIL':>5} {'PASS':>5}  "
          f"{'rung':20} {'red/FAIL':>9} {'red/PASS':>9} {'error':>6} {'median ms':>10}")
    for lang in ORDER + [k for k in sorted(by_lang) if k not in ORDER]:
        sub = by_lang.get(lang)
        if not sub:
            continue
        fails = [r for r in sub if r["truth"]["verdict"] == "FAIL"]
        passes = [r for r in sub if r["truth"]["verdict"] == "PASS"]
        other = [r for r in sub if r["truth"]["verdict"] not in ("PASS", "FAIL")]
        names = []
        for r in sub:
            for n in r["instruments"]:
                if n not in names:
                    names.append(n)
        first = True
        for n in names:
            rf = sum(1 for r in fails if r["instruments"].get(n, {}).get("verdict") == "red")
            rp = sum(1 for r in passes if r["instruments"].get(n, {}).get("verdict") == "red")
            er = sum(1 for r in sub if r["instruments"].get(n, {}).get("verdict") == "error")
            ms = [r["instruments"][n]["ms"] for r in sub if n in r["instruments"]]
            head = (f"{lang:11} {len(sub):>6} {len(fails):>5} {len(passes):>5}  "
                    if first else " " * 32)
            first = False
            print(f"{head}{n:20} {rf:>4}/{len(fails):<4} {rp:>4}/{len(passes):<4} "
                  f"{er:>6} {int(statistics.median(ms)) if ms else 0:>10}")
        if other:
            print(" " * 32 + f"({len(other)} cells whose re-run truth is "
                  f"{sorted({r['truth']['verdict'] for r in other})})")
        print()

    tot_f = sum(1 for r in rows if r["truth"]["verdict"] == "FAIL")
    print(f"{len(rows)} cells, {tot_f} real failures, five languages")


if __name__ == "__main__":
    main()
