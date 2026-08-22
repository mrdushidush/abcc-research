"""Add the `entrypoint` rung to an existing K result file, in place.

The rung was added after the first full pass, and re-running the whole ladder
would re-time every other rung under whatever else the box is doing. This runs
one instrument over the same 54 workdirs and merges it in, so the wall-clock
figures already recorded stay the ones that were measured on a quiet host.

    python add_entrypoint.py
"""

import json

import common as C
import instruments as I

OUT = C.HERE / "results-k.json"


def main():
    rows = json.loads(OUT.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    n = 0
    for d in C.cells(suite="k"):
        if not d["_wd"] or d["_id"] not in by_id:
            continue
        fn = I.make_entrypoint(d["task"])
        with C.Work(d["_wd"]) as w:
            r = fn(w)
        by_id[d["_id"]]["instruments"]["entrypoint"] = r
        n += 1
        print("%-52s entrypoint=%-6s %5dms  %s"
              % (d["_id"], r["verdict"], r["ms"], r["detail"][:60]), flush=True)
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\nmerged into {n} rows")


if __name__ == "__main__":
    main()
