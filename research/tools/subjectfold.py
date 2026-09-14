#!/usr/bin/env python3
"""subjectfold.py - WHICH TREE each anchored attempt was actually handed.

`toolreach.py` splits the anchored cohort at seq 8319 and says why in a comment:

    `4687405` shipped F673's fix; `t8319` at seq 8319 is the first task created
    after it.

The second clause is false, and the log says so in one query. `4687405` landed
15:26:19 on 2026-09-11; `t8319` was created at 16:13:02. Three tasks were created
in between -- t7655 15:45:14, t7999 15:55:49, t8149 16:05:09 -- each its own
`abcc run` process, each launched after the commit. THE FIRST TASK CREATED AFTER
THE FIX IS t7655, and the pivot names a task 28 minutes and four attempts later.

So four Change attempts that were handed the new tool are counted as 'before',
and ONE OF THEM CALLED A CHECKER. That is the single worst direction for the
published figure: it holds a hit in the numerator of the wrong cohort.

  THE BOUNDARY IS READ FROM THE TREE, NOT FROM A CLOCK. Every attempt takes a
`checkpoint_taken`, and `Repo::checkpoint` does `read-tree HEAD` then `git add -A`
over the live repo root, so the checkpoint sha IS the source state that attempt
was handed. Ask it whether it carries the fix instead of inferring from a
timestamp. Both readings agree on t7655, which is why this is a correction and
not a second opinion.

  THE DETECTOR HAS ITS OWN CONTROL. `tools.rs` contains the word "standard" zero
times at `4687405^` and three times at `4687405`. Those two trees are classified
before any unknown one is read: an instrument that cannot separate the two
commits it was built from is not an instrument (F740's rule, one level over).

  WHAT THIS CANNOT SEE. The tool summary the model reads is compiled into the
BINARY; the checkpoint records the SOURCE. They are inferred to agree because a
run is launched from a build, and the log carries only `version: "0.1.0"`. The
correction does not rest on that inference -- the pivot already fails its own
stated rule on task-creation time alone -- but any claim about what a specific
attempt was SHOWN does.

Usage:
    subjectfold.py [--since SEQ]     # the per-attempt fold
    subjectfold.py --stats           # both boundaries over the same events
"""

import argparse
import collections
import datetime
import hashlib
import json
import sqlite3
import subprocess
import sys
from math import comb

DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"
REPO = r"D:\dev\abcc"

ANCHOR = "552a8db2"   # sha1[:8] of the 329-char anchored prompt, 60 tasks
SEQ_PIVOT = 8319      # what toolreach.py uses, and what published F765
SUBJECT_PIVOT = 7663  # the first attempt handed a tree carrying the fix
FIX = "4687405"
PROBE = "crates/abcc-engine/src/tools.rs"
CHECKERS = {"diagnostics", "run_tests"}

# The seq the F765 figures were measured at. Same rule as toolreach.py's AS_OF
# and for the same reason: a control that fails whenever somebody flies a sortie
# gets switched off within a week (F764).
AS_OF = 11726


def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else None


def carries_fix(sha):
    """True if this tree has the rewritten diagnostics summary; None if unreadable."""
    blob = git("show", f"{sha}:{PROBE}") if sha else None
    return None if not blob else blob.count("standard") > 0


def control():
    before, after = carries_fix(f"{FIX}^"), carries_fix(FIX)
    if before is not False or after is not True:
        sys.exit(f"REFUSED: detector cannot separate {FIX}^ ({before}) from {FIX} ({after})")
    print(f"  control: {FIX}^ OLD, {FIX} NEW -- the detector separates them\n")


def fold(db=DB):
    """One row per anchored attempt: task, Change, tools reached, checkpoint tree."""
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    anchor = {t for t, p in con.execute("select id, prompt from task")
              if hashlib.sha1((p or "").encode()).hexdigest()[:8] == ANCHOR}
    rows = [(s, a, json.loads(b)) for s, a, b in
            con.execute("select seq, at_ms, body from event order by seq")]
    att = {}
    for seq, at, e in rows:
        if e["kind"] == "attempt_started" and e.get("task") in anchor:
            att[seq] = {"task": e["task"], "at": at, "change": False,
                        "tools": collections.Counter(), "cp": None}
    for _, _, e in rows:
        a = e.get("attempt")
        if a in att:
            if e["kind"] == "attempt_phase_entered" and e.get("phase") == "change":
                att[a]["change"] = True
            if e["kind"] == "tool_call_started":
                att[a]["tools"][e["tool"]] += 1
    for seq, _, e in rows:      # checkpoint_taken carries the task, not the attempt
        if e["kind"] == "checkpoint_taken":
            prior = [a for a in att if att[a]["task"] == e.get("task") and a < seq]
            if prior and att[max(prior)]["cp"] is None:
                att[max(prior)]["cp"] = e.get("sha")
    return att


def fisher(a, b, c, d):
    """One-sided Fisher exact on [[a, b], [c, d]] -- toolreach.py's, verbatim."""
    n = a + b + c + d
    rowa, cola = a + b, a + c
    lo = max(0, cola - (n - rowa))
    cells = range(lo, min(rowa, cola) + 1)
    total = sum(comb(rowa, i) * comb(n - rowa, cola - i) for i in cells)
    obs = comb(rowa, a) * comb(n - rowa, cola - a)
    tail = sum(comb(rowa, i) * comb(n - rowa, cola - i) for i in cells
               if comb(rowa, i) * comb(n - rowa, cola - i) <= obs)
    return tail / total


def rate(rows, tool=None):
    hit = [r for r in rows if (r["tools"][tool] if tool else
                               any(r["tools"][t] for t in CHECKERS))]
    return len(hit), len(rows)


def line(before, after, tool=None):
    hb, nb = rate(before, tool)
    ha, na = rate(after, tool)
    p = fisher(hb, nb - hb, ha, na - ha)
    print(f"    {tool or 'any checker':<13} {hb:>2}/{nb:<3} {100 * hb / nb:5.1f}%  ->  "
          f"{ha:>2}/{na:<3} {100 * ha / na:5.1f}%   Fisher p = {p:.4f}")


def stats(chg):
    for bound, label in ((AS_OF, f"bounded below AS_OF={AS_OF}, as F765 was"),
                         (10 ** 9, "unbounded, the A4 arm included")):
        rows = {a: v for a, v in chg.items() if a < bound}
        print(f"\n=== {label} -- n={len(rows)} anchored Change attempts ===")
        print(f"\n  A. AS PUBLISHED -- split at seq {SEQ_PIVOT}")
        for t in (None, "diagnostics", "run_tests"):
            line([v for a, v in rows.items() if a < SEQ_PIVOT],
                 [v for a, v in rows.items() if a >= SEQ_PIVOT], t)
        print("\n  B. CORRECTED -- split by the tree the attempt was handed")
        for t in (None, "diagnostics", "run_tests"):
            line([v for v in rows.values() if v["new"] is False],
                 [v for v in rows.values() if v["new"] is True], t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=7000)
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    control()
    att = fold()
    chg = {a: v for a, v in att.items() if v["change"]}
    for v in chg.values():
        v["new"] = carries_fix(v["cp"])

    if args.stats:
        stats(chg)
    else:
        print("  attempt task   when         side  checker      subject tree")
        for a in sorted(chg):
            if a < args.since:
                continue
            v = chg[a]
            label = {True: "NEW diagnostics", False: "OLD diagnostics", None: "unreadable"}[v["new"]]
            got = ",".join(t for t in v["tools"] if t in CHECKERS) or "-"
            when = datetime.datetime.fromtimestamp(v["at"] / 1000).strftime("%m-%d %H:%M")
            side = "PRE " if a < SEQ_PIVOT else "POST"
            print(f"  {a:<7} {v['task']:<6} {when} {side}  {got:<12} {label}")

    mis = sorted(a for a, v in chg.items() if a < SEQ_PIVOT and v["new"] is True)
    print(f"\n  misclassified by the seq pivot: {len(mis)} attempts {mis}")
    for a in mis:
        got = ",".join(t for t in chg[a]["tools"] if t in CHECKERS) or "-"
        print(f"    a{a}  task {chg[a]['task']}  checker: {got}")


if __name__ == "__main__":
    main()
