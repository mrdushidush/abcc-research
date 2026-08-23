#!/usr/bin/env python3
"""W6 item 5 — item 4's cheapest rung, in five languages.

Item 4's winner is the free structural check: *did the change touch any source
file?* It was measured on the K population (9 of 12 behavioural failures, no
false positives, F302) and it is the one rung with no toolchain, no parser and no
language table — so it is the rung whose generality this item has to check.

Here it runs over every preserved Q56 workdir in all five languages. A cell is
`untouched` when every file the fixture shipped is byte-identical in the workdir
and the attempt left no new source file behind. The verifier's residue
(`hidden_gate.*`, which the verifier itself writes) and build caches never count.

Ground truth is `results-q56.json` from `../w6-headroom`, which re-runs the
suite verifier rather than trusting the recorded verdict.

Writes structural-results.json next to this file.
"""

from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
HEADROOM = HERE.parent / "w6-headroom"
sys.path.insert(0, str(HEADROOM))

import common as C  # noqa: E402
import instruments as I  # noqa: E402

SKIP_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
              "target", "node_modules", ".git"}
SOURCE_SUFFIXES = {".py", ".rs", ".mjs", ".js", ".ts", ".sh", ".toml", ".json"}


def rel_files(root: pathlib.Path) -> dict[str, bytes]:
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        # CRLF-normalised, exactly as item 4's `residue.py:37` does it: a file
        # rewritten with different line endings and identical content is not
        # work, and the K overlays are CRLF where the fixtures are LF (F310).
        out[rel.as_posix()] = p.read_bytes().replace(b"\r\n", b"\n")
    return out


def classify(task_id: str, workdir: pathlib.Path) -> dict:
    fixture = rel_files(C.Q56_TASKS / task_id / "fixture")
    work = rel_files(pathlib.Path(workdir))
    residue = set(I.verifier_residue(task_id))

    changed = [k for k, v in fixture.items() if work.get(k) != v]
    deleted = [k for k in fixture if k not in work]
    added = [k for k in work
             if k not in fixture
             and k not in residue
             and pathlib.PurePosixPath(k).suffix in SOURCE_SUFFIXES]
    touched = bool(changed or added or deleted)
    return {
        "touched": touched,
        "changed": sorted(changed),
        "added": sorted(added),
        "deleted": sorted(deleted),
        # green = the change is allowed through; red = "nothing was touched", a veto
        "verdict": "green" if touched else "red",
    }


def k_population() -> None:
    """The same rung over the K population, with item 4's exact rule.

    Item 4 reported 9 of 12 (F302, `residue.py`'s `src_modified` row). Reproduced
    here so the two populations are comparable, and stratified by run, because the
    six W11 budget-sweep cells are arms with an imposed round budget and a pooled
    rate over arms is a fact about the sample (see the Q56 half below).
    """
    res = {r["id"]: r for r in json.loads(
        (HEADROOM / "results-k.json").read_text(encoding="utf-8"))}
    rows = []
    for d in C.cells(suite="k"):
        if not d["_wd"]:
            continue
        fx = rel_files(C.K_TASKS / d["task"] / "fixture")
        wk = rel_files(pathlib.Path(d["_wd"]))
        src_mod = [k for k, v in fx.items()
                   if not (k.startswith("tests/") or "/tests/" in k)
                   and wk.get(k) != v]
        rows.append({"id": d["_id"], "run": d["_run"], "task": d["task"],
                     "status": d["status"],
                     "truth": (res.get(d["_id"], {}).get("truth") or {}).get("verdict", "?"),
                     "verdict": "red" if not src_mod else "green",
                     "src_modified": sorted(src_mod)})
    (HERE / "structural-k-results.json").write_bytes(
        json.dumps(rows, indent=1).encode("utf-8"))
    f = [r for r in rows if r["truth"] == "FAIL"]
    p_ = [r for r in rows if r["truth"] == "PASS"]
    print(f"K: {len(rows)} cells, {len(f)} failures, "
          f"{sum(1 for r in f if r['verdict'] == 'red')} untouched, "
          f"{sum(1 for r in p_ if r['verdict'] == 'red')} false positives of {len(p_)}")
    arms = {}
    for r in f:
        arm = ("k-champ" if r["run"].startswith("k-champ")
               else "k-27b" if r["run"].startswith("k-27b")
               else r["run"].rsplit("-", 1)[0])
        a = arms.setdefault(arm, [0, 0])
        a[0] += 1
        a[1] += r["verdict"] == "red"
    for arm, (n, red) in sorted(arms.items()):
        print(f"   {arm:12} failures {n:>2}  untouched {red:>2}")


def main() -> None:
    if "--k" in sys.argv:
        k_population()
        return
    truth_path = HEADROOM / "results-q56.json"
    truth = {r["id"]: r for r in json.loads(truth_path.read_text(encoding="utf-8"))}
    rows = []
    for d in C.cells(suite="q56"):
        if not d["_wd"]:
            continue
        t = truth.get(d["_uid"])
        r = classify(d["task"], d["_wd"])
        rows.append({
            "id": d["_uid"], "task": d["task"], "lang": I.q56_lang(d["task"]),
            "status": d["status"],
            "recorded": (d.get("verifier") or {}).get("verdict", "-"),
            "truth": (t or {}).get("truth", {}).get("verdict", "?"),
            **r,
        })
    (HERE / "structural-results.json").write_bytes(
        json.dumps(rows, indent=1).encode("utf-8"))

    langs = sorted({r["lang"] for r in rows})
    print(f"{'lang':11} {'cells':>6} {'FAIL':>6} {'red on FAIL':>12} "
          f"{'PASS':>6} {'red on PASS':>12}")
    tot = [0, 0, 0, 0, 0]
    for lang in langs:
        sub = [r for r in rows if r["lang"] == lang]
        f = [r for r in sub if r["truth"] == "FAIL"]
        p = [r for r in sub if r["truth"] == "PASS"]
        rf = sum(1 for r in f if r["verdict"] == "red")
        rp = sum(1 for r in p if r["verdict"] == "red")
        print(f"{lang:11} {len(sub):>6} {len(f):>6} {rf:>12} {len(p):>6} {rp:>12}")
        tot = [tot[0] + len(sub), tot[1] + len(f), tot[2] + rf,
               tot[3] + len(p), tot[4] + rp]
    print(f"{'TOTAL':11} {tot[0]:>6} {tot[1]:>6} {tot[2]:>12} {tot[3]:>6} {tot[4]:>12}")
    unknown = [r for r in rows if r["truth"] == "?"]
    if unknown:
        print(f"\n{len(unknown)} cells have no re-measured truth "
              f"(run ../w6-headroom/ladder.py q56 first)")


if __name__ == "__main__":
    main()
