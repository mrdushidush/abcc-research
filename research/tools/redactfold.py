#!/usr/bin/env python3
r"""redactfold.py - the discriminating arm, asked of trees instead of flown.

LINEAGE P12 left `4687405` (the diagnostics summary the model reads) and
`941add1` (redaction at the tool-result seam, which the model's context passes
through) CONFOUNDED: both landed 2026-09-11, both are model-visible, and every
attempt after the boundary has both. SELFHOST-P1 costed the arm that would
separate them at 100 attempts and 7.2-11.9 GPU hours, for 0.79 power.

  THE TWO COMMITS ARE NOT SIMULTANEOUS, AND THE GAP IS THE ARM.

    941add1  09-11 11:30:10   redaction ships, WITH F712's `(?i)` bug
    7fe980f  09-11 15:18:51   the green ladder ending
    4687405  09-11 15:26:19   the diagnostics summary
    3e5a04b  09-12 11:32:33   F712 - the `(?i)` bug fixed

So a tree in the 3h56m between 941add1 and 4687405 carries the REDACTION and the
OLD diagnostics summary. That is the cell the arm was going to buy, and if any
anchored attempt was handed such a tree it is already on the log.

  AND THE BUG IS THE MECHANISM, NOT A DETAIL. F712: with `(?i)` the Assignment
shape matched the English word `secrets`, so `pub fn secrets(mut self, secrets:
Secrets) ->` reached the model as `secrets: [redacted] ->` -- the type gone and
the closing paren with it. FOURTEEN of this workspace's 132 files were rewritten
before a model saw them. A model shown corrupted source is a plausible cause of
almost any behaviour change, which is exactly why it may not stay confounded
with the other one.

  THE DETECTOR HAS ITS OWN CONTROL, AND MY FIRST TWO PROBES FAILED IT.
Counting `(?i)` in redact.rs INVERTS across the fix (2 -> 3), because F712 adds
two mentions in comments while removing one from the regex. Grepping
`(?i)(?P<keep>` matches at HEAD, because the AuthHeader shape begins with the
same eight characters. The probe that works is anchored on the Assignment shape
alone, and `control()` refuses to read an unknown tree until it has separated
the two commits it was built from (F740's rule).

  WHAT THIS CANNOT SEE is subjectfold.py's caveat, unchanged and load-bearing:
the checkpoint records the SOURCE and the behaviour comes from the BINARY. A run
is launched from a build, so they are inferred to agree; the log carries only
`version: "0.1.0"`. Every claim here is about the tree an attempt was handed.

Read-only. Nothing here writes to the log or to the repository.

Usage:
    redactfold.py            # the 2x2 and the per-attempt fold
    redactfold.py --stats    # the cell counts only
"""

import argparse
import collections
import hashlib
import json
import sqlite3
import subprocess
import sys

DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"
REPO = r"D:\dev\abcc"

ANCHOR = "552a8db2"          # sha1[:8] of the 329-char anchored prompt
CHECKERS = {"diagnostics", "run_tests"}

REDACT = "crates/abcc-core/src/redact.rs"
TOOLS = "crates/abcc-engine/src/tools.rs"

# The Assignment shape while it was case-insensitive. NOT `(?i)(?P<keep>`, which
# the AuthHeader shape also begins with, and NOT a count of `(?i)`, which the
# fix's own comments invert.
BUGGY = r"(?i)(?P<keep>\b[A-Z0-9_]*"

REDACTION_FIX = "3e5a04b"    # F712 - the `(?i)` came off the Assignment shape
REDACTION_IN = "941add1"     # redact.rs first exists
DIAG_FIX = "4687405"         # F673 - diagnostics runs the standard

AS_OF = 11726                # F764's rule, same constant toolreach.py carries


def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args],
                       capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else None


def redaction_of(sha):
    """'none' | 'buggy' | 'fixed' for the tree at `sha`; None if unreadable."""
    if not sha:
        return None
    blob = git("show", f"{sha}:{REDACT}")
    if blob is None:
        # Distinguish 'the file is not in this tree' from 'the tree is gone'.
        return "none" if git("cat-file", "-e", f"{sha}^{{tree}}") is not None else None
    return "buggy" if BUGGY in blob else "fixed"


def diagnostics_of(sha):
    """True if this tree's diagnostics runs the standard (F673's fix)."""
    if not sha:
        return None
    blob = git("show", f"{sha}:{TOOLS}")
    return None if blob is None else blob.count("standard") > 0


def control():
    """Refuse to classify anything until both detectors separate their commits."""
    checks = [
        ("redaction", REDACTION_IN, redaction_of(f"{REDACTION_IN}^"), "none",
         redaction_of(REDACTION_IN), "buggy"),
        ("redaction", REDACTION_FIX, redaction_of(f"{REDACTION_FIX}^"), "buggy",
         redaction_of(REDACTION_FIX), "fixed"),
        ("diagnostics", DIAG_FIX, diagnostics_of(f"{DIAG_FIX}^"), False,
         diagnostics_of(DIAG_FIX), True),
    ]
    for name, sha, before, want_b, after, want_a in checks:
        if before != want_b or after != want_a:
            sys.exit(f"REFUSED: the {name} detector cannot separate {sha}^ "
                     f"({before!r}, wanted {want_b!r}) from {sha} "
                     f"({after!r}, wanted {want_a!r})")
        print(f"  control: {name:11s} {sha}^ {before!r} -> {sha} {after!r}")
    print()


def fold(db=DB, below=AS_OF):
    """One row per anchored attempt with a Change phase, and its tree."""
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    anchor = {t for t, p in con.execute("select id, prompt from task")
              if hashlib.sha1((p or "").encode()).hexdigest()[:8] == ANCHOR}
    rows = [(s, json.loads(b)) for s, b in
            con.execute("select seq, body from event order by seq")]
    att = {}
    for seq, e in rows:
        if e["kind"] == "attempt_started" and e.get("task") in anchor:
            att[seq] = {"task": e["task"], "change": False,
                        "tools": collections.Counter(), "cp": None}
    for _, e in rows:
        a = e.get("attempt")
        if a in att:
            if e["kind"] == "attempt_phase_entered" and e.get("phase") == "change":
                att[a]["change"] = True
            if e["kind"] == "tool_call_started":
                att[a]["tools"][e["tool"]] += 1
    for seq, e in rows:      # checkpoint_taken carries the task, not the attempt
        if e["kind"] == "checkpoint_taken":
            prior = [a for a in att if att[a]["task"] == e.get("task") and a < seq]
            if prior and att[max(prior)]["cp"] is None:
                att[max(prior)]["cp"] = e.get("sha")
    return {a: r for a, r in att.items() if r["change"] and (below is None or a < below)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stats", action="store_true")
    args = p.parse_args()

    print(f"\nredactfold - the 2x2 the arm was going to buy, read off the trees\n")
    control()

    att = fold()
    cells = collections.defaultdict(list)
    unreadable = 0
    for a, r in sorted(att.items()):
        red, diag = redaction_of(r["cp"]), diagnostics_of(r["cp"])
        if red is None or diag is None:
            unreadable += 1
            continue
        r["redaction"], r["diagnostics"] = red, diag
        cells[(red, diag)].append(a)

    print(f"anchored Change attempts below seq {AS_OF}: {len(att)}"
          f"   ({unreadable} whose tree is no longer readable)\n")
    print(f"{'redaction':<12} {'diagnostics':<13} {'n':>3} {'checker':>8} {'rate':>7}")
    order = [("none", False), ("buggy", False), ("buggy", True),
             ("fixed", False), ("fixed", True), ("none", True)]
    for key in order:
        ids = cells.get(key)
        if not ids:
            continue
        hit = sum(1 for a in ids if CHECKERS & set(att[a]["tools"]))
        red, diag = key
        label = "NEW" if diag else "OLD"
        print(f"{red:<12} {label:<13} {len(ids):>3} {hit:>8} "
              f"{hit / len(ids) * 100:>6.1f}%")

    sep = cells.get(("buggy", False), [])
    print()
    if sep:
        print(f"THE SEPARATING CELL IS POPULATED: {len(sep)} attempt(s) carry the "
              f"redaction with the OLD diagnostics summary -- {sep}")
    else:
        print("THE SEPARATING CELL IS EMPTY. No anchored attempt was handed a tree")
        print("with the redaction and the old diagnostics summary, so the log cannot")
        print("separate 941add1 from 4687405 on its own and the arm is still the only")
        print("instrument that can. This is a NEGATIVE RESULT, not a missing number.")

    if not args.stats:
        print(f"\n{'attempt':>8} {'task':>6} {'redaction':<10} {'diag':<5} tools")
        for a, r in sorted(att.items()):
            if "redaction" not in r:
                continue
            reached = "".join(sorted(CHECKERS & set(r["tools"]))) or "-"
            print(f"{a:>8} {r['task']:>6} {r['redaction']:<10} "
                  f"{'NEW' if r['diagnostics'] else 'OLD':<5} {reached}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
