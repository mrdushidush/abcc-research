"""Which real agent workdirs exist, with what ground truth, for W6 item 4.

No arguments, no scratchpad: reads `runs/*/*/cells.jsonl` in this repository and
reports every K-suite cell whose workdir survived, with the verdict the suite's
own verifier recorded at the time.
"""

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
RUNS = REPO / "runs"


def cells():
    for jl in sorted(RUNS.glob("*/*/cells.jsonl")):
        for line in jl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            wd = d.get("workdir", "")
            # recorded as `../runs/<run>\...`, relative to the harness dir
            p = (REPO / wd.replace("../", "").replace("\\", "/")) if wd else None
            d["_wd"] = p
            d["_run"] = jl.parent.parent.name
            yield d


def main():
    by = {}
    for d in cells():
        key = (d["suite"], d["status"], bool(d["_wd"] and d["_wd"].is_dir()))
        by[key] = by.get(key, 0) + 1
    print(f"{'suite':6} {'status':9} {'wd?':5} {'n':>4}")
    for k in sorted(by):
        print(f"{k[0]:6} {k[1]:9} {str(k[2]):5} {by[k]:>4}")

    print("\nK cells with a surviving workdir:")
    print(f"{'run':22} {'task':34} {'status':9} verdict")
    n = 0
    for d in cells():
        if d["suite"] != "k":
            continue
        if not (d["_wd"] and d["_wd"].is_dir()):
            continue
        n += 1
        v = (d.get("verifier") or {}).get("verdict", "-")
        print(f"{d['_run']:22} {d['task']:34} {d['status']:9} {v}")
    print(f"\n{n} K workdirs")


if __name__ == "__main__":
    main()
