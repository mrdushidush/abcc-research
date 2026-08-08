#!/usr/bin/env python3
"""Rank the 90 stable ABCC tasks, and select the 30 that get the three-point gate.

Inputs:
  tasks.json                                  (from extract_tasks.py, donor d5528ea)
  ../../../prestudy/data/abcc-100task-results.tsv   (7 recorded runs, long form)

Two axes, deliberately:

  A. Observed difficulty  — genuine failures and timeouts across the 5 clean runs.
     Separates only ~13 tasks; the suite saturates.
  B. Verifier exposure    — what the verifier claims minus what it checks. This is
     the axis a sham actually tests, so it carries the tie-break.

Run: python rank.py
"""
import collections
import csv
import json
import re
import statistics
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / ".." / ".." / ".." / "prestudy" / "data" / "abcc-100task-results.tsv"

# The 2026-02-26 run is an infrastructure collapse: 72 errors, median duration 2 s,
# every one 'fetch failed' because the endpoint was down. Note that the clean runs
# ALSO carry 'fetch failed' errors — at 307 s, i.e. the 300 s TASK_TIMEOUT_MS.
# Same string, opposite meaning. Exclude by run, never by error text.
COLLAPSE = "2026-02-26T11-04-01"
TIMEOUT_S = 300

# react_cto / cto_decomposed ran once or twice as a decomposition experiment and are
# not part of the stable 90. The corpus format defers decomposition to a later version.
UNSTABLE = ("react_cto", "cto_decomposed")


def verifier_class(t):
    """How much does this verifier actually establish?

    none      — validation is null; runner scores on execSuccess alone (:3168)
    strmatch  — reads the produced file and asserts substrings are present
    exec      — imports/requires the produced artifact and asserts on behaviour
    """
    v = t.get("validation")
    if not v or v.strip() == "null":
        return "none"
    executes = bool(
        re.search(r"from tasks\.|__import__|subprocess|exec\(|importlib|require\(", v)
    )
    return "exec" if executes else "strmatch"


def load():
    tasks = {t["name"]: t for t in json.loads((HERE / "tasks.json").read_text("utf-8"))}
    rows = list(csv.DictReader(RESULTS.open(encoding="utf-8"), delimiter="\t"))
    clean = [r for r in rows if r["run"] != COLLAPSE and r["status"] != "dry_run"]

    by_task = collections.defaultdict(list)
    for r in clean:
        by_task[r["task"]].append(r)

    out = []
    for name, rs in by_task.items():
        t = tasks.get(name)
        if t is None or t.get("category") in UNSTABLE:
            continue
        durs = [int(r["duration_s"]) for r in rs]
        fails = [r for r in rs if r["status"] == "failed"]
        errs = [r for r in rs if r["status"] == "error"]
        timeouts = [r for r in errs if int(r["duration_s"]) >= TIMEOUT_S]
        ok = [int(r["duration_s"]) for r in rs if r["status"] == "passed"]
        out.append(
            dict(
                name=name,
                category=t["category"],
                section=int(t["section"]),
                complexity=int(t["complexity"]),
                vclass=verifier_class(t),
                _v=t.get("validation") or "",
                runs=len(rs),
                fails=len(fails),
                timeouts=len(timeouts),
                other_err=len(errs) - len(timeouts),
                med_ok=statistics.median(ok) if ok else None,
                max_dur=max(durs),
                durs=durs,
            )
        )
    return out


def observed_difficulty(t):
    """Failures and timeouts are both genuine difficulty; a timeout is a task the
    subject could not finish in 5 minutes. Normalised by runs so the 5-run react
    tasks are comparable with the 4-run rest."""
    return (t["fails"] + t["timeouts"]) / t["runs"]


def main():
    tasks = load()
    assert len(tasks) == 90, len(tasks)

    print(f"stable pool: {len(tasks)} tasks, "
          f"{sum(1 for t in tasks if t['runs'] == 5)} with 5 clean runs, "
          f"{sum(1 for t in tasks if t['runs'] == 4)} with 4\n")

    print("=== verifier classes across the stable 90 ===")
    vc = collections.Counter(t["vclass"] for t in tasks)
    for k in ("exec", "strmatch", "none"):
        cats = collections.Counter(t["category"] for t in tasks if t["vclass"] == k)
        print(f"  {k:9s} {vc[k]:3d}   {dict(cats)}")

    print("\n=== axis A: observed difficulty (any failure or timeout) ===")
    hard = sorted(
        [t for t in tasks if observed_difficulty(t) > 0],
        key=lambda t: (-observed_difficulty(t), -(t["med_ok"] or 999)),
    )
    print(f"  {len(hard)} of 90 tasks show any negative signal at all\n")
    print("     task                       cat        cx  runs  F  TO  rate  med_ok  verifier")
    for i, t in enumerate(hard, 1):
        print(f"  {i:2d} {t['name']:<26} {t['category']:<10} {t['complexity']}  "
              f"{t['runs']:4d} {t['fails']:2d} {t['timeouts']:3d}  "
              f"{observed_difficulty(t):.2f}  {str(t['med_ok']):>6}  {t['vclass']}")

    print("\n=== the saturation wall ===")
    rest = [t for t in tasks if observed_difficulty(t) == 0]
    meds = sorted(t["med_ok"] for t in rest)
    print(f"  {len(rest)} tasks passed every clean run. Median duration spread: "
          f"{meds[0]:.0f}s .. {meds[-1]:.0f}s, p50 {statistics.median(meds):.0f}s")
    print("  Duration below the timeout tracks output length, not difficulty — "
          "it cannot carry a 17-task tie-break.")

    select(tasks)
    return tasks, hard


# --- axis B: verifier exposure, which carries the tie-break -------------------

def n_checks(v):
    """Distinct behavioural claims the verifier makes. The node one-liners express
    several checks inside one compound `if`, so && / || count."""
    n = len(re.findall(r"\bassert\b", v))
    n += len(re.findall(r"process\.exit\(1\)|throw new Error", v))
    n += len(re.findall(r"&&|\|\|", v))
    return max(n, 1)


def select(tasks):
    """The 30 that get the three-point gate.

    "Hardest" is read operationally as *where a sham is most likely to pass*, because
    the sham is the only thing the third gate point adds. On that reading two whole
    blocks drop out — not because they are easy, but because their gate outcome is
    already known and authoring a sham for them would produce no information:

      none      (10, ts+go)          — no verifier; every sham passes by construction
      strmatch  (24, react+landing)  — substring presence; a sham with the tokens in a
                                       comment passes, and the task has no ground truth
                                       to be wrong about in the first place

    That leaves the 56 executing verifiers as the only population where a sham is
    real work with an unknown answer.
    """
    exec_pool = [t for t in tasks if t["vclass"] == "exec"]
    sec4 = [t for t in exec_pool if t["section"] == 4]
    rest = [t for t in exec_pool if t["section"] != 4]

    # Tier 1: all of section 4. It holds 11 of the 12 observed-hard tasks, it is the
    # only block asserting a *negative* property ("the vulnerability is gone") — the
    # class assertion-chains demonstrably fail at — and it is the only section where
    # the agent reads an existing file instead of generating from nothing.
    tier1 = sorted(sec4, key=lambda t: (-observed_difficulty(t), t["name"]))

    # Tier 2: 10 more from the other 36. Observed difficulty first, then the most
    # under-checked verifiers, capped at 3 per category so the spread survives.
    forced = [t for t in rest if observed_difficulty(t) > 0]
    ranked = sorted(
        (t for t in rest if t not in forced),
        key=lambda t: (n_checks(t["_v"]) / t["complexity"], -t["complexity"], t["name"]),
    )
    tier2, per_cat = list(forced), collections.Counter(t["category"] for t in forced)
    seen_cats = set(per_cat)
    # Two passes. The first reserves the tail slots for categories not yet covered,
    # so the tier does not collapse onto node_api; the second fills whatever is left.
    for reserve in (True, False):
        for t in ranked:
            if len(tier2) >= 10:
                break
            if t in tier2 or per_cat[t["category"]] >= 3:
                continue
            if reserve and len(tier2) >= 8 and t["category"] in seen_cats:
                continue
            tier2.append(t)
            per_cat[t["category"]] += 1
            seen_cats.add(t["category"])

    chosen = tier1 + tier2
    print(f"\n=== the 30: {len(tier1)} tier-1 (all of section 4) "
          f"+ {len(tier2)} tier-2 (most under-checked elsewhere) ===\n")
    print("      task                       cat        sec cx  F/TO  chk/cx  why")
    for i, t in enumerate(chosen, 1):
        why = ("observed" if observed_difficulty(t) > 0 else
               ("section 4" if t["section"] == 4 else "under-checked"))
        print(f"  {i:2d}  {t['name']:<26} {t['category']:<10} {t['section']}   "
              f"{t['complexity']}  {t['fails']}/{t['timeouts']}   "
              f"{n_checks(t['_v'])/t['complexity']:.2f}    {why}")
    print(f"\n  category spread: {dict(collections.Counter(t['category'] for t in chosen))}")
    print(f"  section spread:  {dict(collections.Counter(t['section'] for t in chosen))}")
    excluded = collections.Counter(
        t["vclass"] for t in tasks if t["vclass"] != "exec")
    print(f"  excluded by verifier class: {dict(excluded)} "
          f"(+{len(exec_pool) - len(chosen)} executing verifiers not selected)")
    return chosen


if __name__ == "__main__":
    main()
