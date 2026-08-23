#!/usr/bin/env python3
"""W6 item 5 — is the rung red *before* anyone touches the tree?

An instrument that is red on the unfixed fixture and red on the reference
solution carries no information about the change, however impressive its verdict
count looks. Item 4 found that for `ruff` and `mypy --strict` on the K fixtures
(F300); the Q56 typescript half needs the same control, because `tsc` is red on
every cell in that language — 10 of 10 failures and 80 of 80 passes — and a rate
like that is either a very good instrument or a pre-existing condition.

So: run every language's ladder over the pristine **fixture** and over the
**refsol** of each Q56 task, where truth is by construction.

Reads the corpus, writes baseline-results.json next to this file.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
HEADROOM = HERE.parent / "w6-headroom"
sys.path.insert(0, str(HEADROOM))

import common as C  # noqa: E402
import instruments as I  # noqa: E402


def overlay(task_id: str, which: str, dest: pathlib.Path) -> pathlib.Path:
    """A fresh copy of the fixture, optionally with the refsol laid over it."""
    task = C.Q56_TASKS / task_id
    shutil.copytree(task / "fixture", dest)
    if which == "refsol":
        src = task / "refsol"
        if not src.is_dir():
            return dest
        for p in src.rglob("*"):
            if p.is_file():
                rel = p.relative_to(src)
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dest / rel)
    return dest


def main() -> None:
    rows = []
    for task_id in sorted(p.name for p in C.Q56_TASKS.iterdir() if p.is_dir()):
        lang, rungs = I.q56_ladder(task_id)
        if not rungs:
            continue
        has_refsol = (C.Q56_TASKS / task_id / "refsol").is_dir()
        for which in ["fixture"] + (["refsol"] if has_refsol else []):
            tmp = pathlib.Path(tempfile.mkdtemp(prefix="w6lang-"))
            try:
                work = overlay(task_id, which, tmp / "work")
                row = {"task": task_id, "lang": lang, "tree": which,
                       "instruments": {}}
                for name, fn in rungs:
                    with C.Work(work) as w:
                        row["instruments"][name] = fn(w)
                rows.append(row)
                print(f"{task_id:5} {lang:11} {which:8} "
                      + "  ".join(f"{n}={row['instruments'][n]['verdict']}"
                                  for n in row["instruments"]), flush=True)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    (HERE / "baseline-results.json").write_bytes(
        json.dumps(rows, indent=1).encode("utf-8"))

    print()
    langs = sorted({r["lang"] for r in rows})
    for lang in langs:
        sub = [r for r in rows if r["lang"] == lang]
        names = sorted({n for r in sub for n in r["instruments"]})
        for n in names:
            for which in ["fixture", "refsol"]:
                cells = [r for r in sub if r["tree"] == which and n in r["instruments"]]
                red = sum(1 for r in cells if r["instruments"][n]["verdict"] == "red")
                err = sum(1 for r in cells if r["instruments"][n]["verdict"] == "error")
                if cells:
                    print(f"{lang:11} {n:20} {which:8} red {red:>2}/{len(cells):<2} "
                          f"error {err}")
        print()


if __name__ == "__main__":
    main()
