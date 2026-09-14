#!/usr/bin/env python3
"""toolreach.py - which tools an attempt REACHED FOR, folded per attempt.

The question this exists for is F673's second half. `diagnostics` was
`cargo check --all-targets`; since `4687405` it also runs the standard the
repository declares for itself -- `cargo fmt --check` then
`cargo clippy --all-targets -- -D warnings`, the gate's own commands -- and its
summary was rewritten to say so. Whether the model then REACHES FOR it is a
different question from whether the tool is right, and only the log can answer
it.

  THE DENOMINATOR IS THE ATTEMPT THAT COULD HAVE CALLED IT, NOT THE ATTEMPT.
An attempt that never entered a Change phase had no occasion to run a checker,
so counting it in the denominator dilutes the rate with attempts that were never
asked the question. This is F749's rule one level over: the denominator is the
unit of DECISION.

  THE CONTROL IS A TOTAL THAT MUST BE NON-ZERO (F740). 2,218 tool calls are
known to exist on the abcc log; a fold that sums to zero is wrong before its
content is read. `--check` asserts the published numbers so a drift is visible
before a new figure is quoted.

Usage:
    toolreach.py <log.sqlite> [--pivot SEQ] [--since SEQ] [--tool NAME]
    toolreach.py <log.sqlite> --check
"""

import argparse
import collections
import json
import sqlite3
import sys

# `4687405` shipped F673's fix; `t8319` at seq 8319 is the first task created
# after it. Attempts at or above this seq saw the tool that measures the
# standard; attempts below it saw `cargo check` and the old summary.
#
#   🚨 THE SECOND CLAUSE ABOVE IS FALSE AND THIS CONSTANT IS OFF BY THREE TASKS
# (F767). `4687405` landed 15:26:19 on 2026-09-11; `t8319` was created 16:13:02.
# Created in between, each after the commit and each its own `abcc run`: t7655
# 15:45:14, t7999 15:55:49, t8149 16:05:09. The first task created after the fix
# is t7655, not t8319, and reading the `checkpoint_taken` trees back agrees --
# a7663 is the first attempt handed a tree carrying the new summary.
#
# So four Change attempts that had the new tool are counted here as 'before', and
# a8007 -- one of the four -- CALLED `run_tests`. Corrected, F765's class result
# survives and weakens: any checker 24.5% -> 0.0% p = 0.0139 becomes
# 24.4% -> 4.2% p = 0.0457, and the twenty consecutive zeros are twenty-four
# attempts with one hit in them. See `subjectfold.py`, which folds both.
#
#   THIS CONSTANT IS LEFT WHERE IT IS ON PURPOSE. `PUBLISHED` below was measured
# with it, `--check` reproduces all seven, and the figures are correctly COMPUTED
# -- what was wrong is what the boundary means. F764's rule applies unchanged:
# repair by adding what is missing, never by quietly moving a published number
# under a reader who will quote it. Restating F765 is David's call, not a sed.
F673_PIVOT = 8319

# Where the boundary actually falls, read from the subject trees (F767).
SUBJECT_PIVOT = 7663

# The seq the published numbers were measured AT. Everything at or above it is a
# later sortie, so `--check` bounds the cohorts here.
#   WITHOUT THIS THE CONTROL EATS ITSELF. The first run of `--check` was made
# while an arm was flying and it reported DRIFT on two numbers -- correctly, the
# log really had 27 attempts and 2,230 calls by then. A control that fails
# whenever anybody flies a sortie gets switched off within a week, and the drift
# it was built to catch goes with it. The published figures describe a
# population as of a moment; the bound is part of the figure.
AS_OF = 11726

# What `--check` must reproduce, over events below AS_OF. Measured 2026-09-14 on
# the abcc log. If one of these moves, the log moved and every rate is stale.
PUBLISHED = {
    "tool_calls_total": 2218,
    "before_attempts": 72,
    "before_change": 63,
    "before_reached": 6,
    "after_attempts": 26,
    "after_change": 24,
    "after_reached": 0,
}


def load(path):
    con = sqlite3.connect(path)
    return [(s, json.loads(b)) for s, b in con.execute("select seq, body from event order by seq")]


def fold(rows, tool="diagnostics", below=None):
    """One row per attempt: the task, whether it had a Change phase, its tools."""
    if below is not None:
        rows = [(s, e) for s, e in rows if s < below]
    attempts = {}
    for seq, e in rows:
        if e["kind"] == "attempt_started":
            attempts[seq] = {
                "task": e["task"],
                "tools": collections.Counter(),
                "change": False,
            }
    calls = 0
    for _, e in rows:
        a = e.get("attempt")
        if a not in attempts:
            continue
        if e["kind"] == "tool_call_started":
            # The field is `tool`; `name` is accepted because an older writer
            # used it, and a fold keyed on the wrong field reads zero without
            # saying so.
            attempts[a]["tools"][e.get("tool") or e.get("name")] += 1
            calls += 1
        elif e["kind"] == "attempt_phase_entered" and "change" in str(e.get("phase", "")).lower():
            attempts[a]["change"] = True
    return attempts, calls


def cohort(attempts, lo, hi, tool):
    """(attempts, those with a Change phase, those that reached for `tool`)."""
    rows = [d for a, d in attempts.items() if lo <= a < hi]
    change = [d for d in rows if d["change"]]
    reached = [d for d in change if d["tools"][tool]]
    return len(rows), len(change), len(reached)


def fisher(a, b, c, d):
    """One-sided Fisher exact on [[a, b], [c, d]]. No scipy on this box."""
    from math import comb

    n = a + b + c + d
    rowa, cola = a + b, a + c
    lo = max(0, cola - (n - rowa))
    total = sum(comb(rowa, i) * comb(n - rowa, cola - i) for i in range(lo, min(rowa, cola) + 1))
    obs = comb(rowa, a) * comb(n - rowa, cola - a)
    tail = sum(
        comb(rowa, i) * comb(n - rowa, cola - i)
        for i in range(lo, min(rowa, cola) + 1)
        if comb(rowa, i) * comb(n - rowa, cola - i) <= obs
    )
    return tail / total, obs / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--pivot", type=int, default=F673_PIVOT)
    ap.add_argument("--since", type=int, default=None, help="a third cohort, for a new arm")
    ap.add_argument("--tool", default="diagnostics")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    rows = load(args.log)
    attempts, calls = fold(rows, args.tool, below=AS_OF if args.check else None)

    # F740's control, first: a total that must be non-zero.
    if calls == 0:
        print("REFUSED: 0 tool calls folded. The key is wrong, not the log.", file=sys.stderr)
        return 2

    big = 10**18
    b_all, b_chg, b_got = cohort(attempts, 0, args.pivot, args.tool)
    a_all, a_chg, a_got = cohort(attempts, args.pivot, big, args.tool)

    if args.check:
        # Recomputed inside the bound, so the control is about the same
        # population the figures were published over.
        b_all, b_chg, b_got = cohort(attempts, 0, args.pivot, args.tool)
        a_all, a_chg, a_got = cohort(attempts, args.pivot, AS_OF, args.tool)
        got = {
            "tool_calls_total": calls,
            "before_attempts": b_all,
            "before_change": b_chg,
            "before_reached": b_got,
            "after_attempts": a_all,
            "after_change": a_chg,
            "after_reached": a_got,
        }
        bad = {k: (v, PUBLISHED[k]) for k, v in got.items() if v != PUBLISHED[k]}
        for k, (g, p) in sorted(bad.items()):
            print(f"DRIFT  {k}: log says {g}, published {p}")
        if bad:
            print(f"\n{len(bad)} of {len(PUBLISHED)} published numbers no longer reproduce.")
            return 1
        print(f"--check OK: all {len(PUBLISHED)} published numbers reproduce.")
        return 0

    print(f"log: {len(rows)} events, {calls} tool calls, {len(attempts)} attempts")
    print(f"tool under test: {args.tool}   pivot: seq {args.pivot}\n")
    print(f"{'cohort':22s} {'attempts':>9s} {'w/ Change':>10s} {'reached':>8s}  rate")
    for name, (al, ch, gt) in [
        (f"before {args.pivot}", (b_all, b_chg, b_got)),
        (f"from {args.pivot}", (a_all, a_chg, a_got)),
    ]:
        rate = f"{gt}/{ch}" + (f" = {gt / ch:.1%}" if ch else "")
        print(f"{name:22s} {al:9d} {ch:10d} {gt:8d}  {rate}")

    if args.since is not None:
        s_all, s_chg, s_got = cohort(attempts, args.since, big, args.tool)
        rate = f"{s_got}/{s_chg}" + (f" = {s_got / s_chg:.1%}" if s_chg else "")
        print(f"{'arm from ' + str(args.since):22s} {s_all:9d} {s_chg:10d} {s_got:8d}  {rate}")

    if b_chg and a_chg:
        p, _ = fisher(b_got, b_chg - b_got, a_got, a_chg - a_got)
        print(f"\nFisher (two-sided) before vs after: p = {p:.3f}")
        if p > 0.05:
            print("  NOT significant. The zero is consistent with the old rate at this n.")

    print("\nper-attempt tools, newest 12:")
    for a, d in sorted(attempts.items())[-12:]:
        mark = " <-- reached" if d["tools"][args.tool] else ""
        print(f"  a{a} t{d['task']:<6d} change={d['change']!s:5s} {dict(d['tools'])}{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
