#!/usr/bin/env python3
r"""armscore.py - score the REDACT arm against the rule fixed before it flew.

The rule is hard-coded here and was written into
`research/SELFHOST-P3-the-arm-that-was-a-query.md` section 7 at 2026-09-18 15:42:26,
sha256 20ff59790e87e4da0414d855d1081f1c938b89e9c95ba06b3610cedc0dff83b9, BEFORE the
model was loaded. It is repeated rather than re-derived so that scoring cannot
quietly become choosing.

    tree      4687405^ = 7fe980f   buggy redaction, OLD diagnostics summary
    n         15 attempts WITH a Change phase; others are replaced, not counted
    outcome   the attempt reached `diagnostics` or `run_tests`
    rule      <=1 hit  -> REDACTION (941add1) is the lever
              >=2 hits -> DIAGNOSTICS (4687405) is the lever
    stopping  no early look, no extension

  THE CELL IS A CONTROL, NOT AN ASSUMPTION. Every checkpoint the arm took is
classified with `redactfold.py`'s detectors, and this refuses to print a verdict
if any of them is outside the buggy/OLD cell -- an arm that drifted out of its
own cell is not the arm that was registered.

Read-only.

Usage:  armscore.py [--home <dir>]
"""

import argparse
import collections
import json
import sqlite3
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
import redactfold as rf  # noqa: E402

HOME = r"C:\Users\david\AppData\Local\abcc\arm-redact-7fe980f"
N_REGISTERED = 15
CHECKERS = rf.CHECKERS          # the same set, not a second copy
RULE_THRESHOLD = 2              # >= this many hits favours DIAGNOSTICS


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--home", default=HOME)
    args = p.parse_args()

    db = args.home.rstrip("\\/") + r"\log.sqlite"
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)

    att = {}
    for seq, body in con.execute("select seq, body from event order by seq"):
        e = json.loads(body)
        if e["kind"] == "attempt_started":
            att[seq] = {"task": e.get("task"), "change": False,
                        "tools": collections.Counter(), "cp": None, "ending": None}
        a = e.get("attempt")
        if a in att:
            if e["kind"] == "attempt_phase_entered" and e.get("phase") == "change":
                att[a]["change"] = True
            if e["kind"] == "tool_call_started":
                att[a]["tools"][e["tool"]] += 1
            if e["kind"] == "attempt_ended":
                att[a]["ending"] = e.get("outcome")
    for seq, body in con.execute(
            "select seq, body from event where kind='checkpoint_taken' order by seq"):
        e = json.loads(body)
        prior = [a for a in att if att[a]["task"] == e.get("task") and a < seq]
        if prior and att[max(prior)]["cp"] is None:
            att[max(prior)]["cp"] = e.get("sha")

    print(f"\nREDACT arm - scored against the rule fixed at 2026-09-18 15:42:26\n")

    # --- the cell control, before any count is printed ---------------------
    bad = []
    for a, r in att.items():
        if not r["cp"]:
            continue
        red, diag = rf.redaction_of(r["cp"]), rf.diagnostics_of(r["cp"])
        if red != "buggy" or diag is not False:
            bad.append((a, r["cp"], red, diag))
    if bad:
        print("REFUSED: these attempts are outside the registered buggy/OLD cell:")
        for a, cp, red, diag in bad:
            print(f"  a{a} {cp[:12]} redaction={red} diagnostics={'NEW' if diag else 'OLD'}")
        return 1
    print(f"  cell control: every checkpoint is buggy redaction + OLD diagnostics  [ok]")

    # The orphan rule, declared 16:07 before any kill occurred: an attempt with no
    # ending was killed by the flight script's `timeout 1200` and is NOT a completed
    # observation. Truncation can only push an attempt toward "no checker", which is
    # the direction the prediction wants -- so it is replaced, never counted.
    orphans = [a for a, r in att.items() if r["change"] and r["ending"] is None]
    changed = {a: r for a, r in att.items() if r["change"] and r["ending"] is not None}
    print(f"  attempts started {len(att)}, with a Change phase and an ending "
          f"{len(changed)} (registered n = {N_REGISTERED})")
    if orphans:
        print(f"  orphans excluded by the 16:07 rule (killed, not observations): "
              f"{['a%d' % a for a in orphans]}")

    if len(changed) < N_REGISTERED:
        print(f"\nINCOMPLETE: {len(changed)} of {N_REGISTERED}. Not scoring - the stopping"
              f" rule says all {N_REGISTERED} fly before the count is read.")
        return 2

    scored = sorted(changed)[:N_REGISTERED]
    hits = [a for a in scored if CHECKERS & set(changed[a]["tools"])]

    print(f"\n{'attempt':>8} {'ending':<22} {'checker':<22} tools")
    for a in scored:
        r = changed[a]
        # `ending` is already the parsed body, not a string.
        end = (r["ending"] or {}).get("outcome", "?") if isinstance(r["ending"], dict) \
            else (r["ending"] or "?")
        reached = ", ".join(sorted(CHECKERS & set(r["tools"]))) or "-"
        tools = " ".join(f"{t}x{n}" for t, n in r["tools"].most_common())
        print(f"{a:>8} {str(end):<22} {reached:<22} {tools[:60]}")

    k = len(hits)
    print(f"\n  checker hits: {k} of {N_REGISTERED}  ({k / N_REGISTERED * 100:.1f}%)")
    print(f"  expected under REDACTION   ~4.2%  -> 0-1 hits")
    print(f"  expected under DIAGNOSTICS ~24.4% -> ~3-4 hits")
    verdict = "DIAGNOSTICS (4687405)" if k >= RULE_THRESHOLD else "REDACTION (941add1)"
    print(f"\n  THE RULE SAYS: {verdict}")
    print(f"  (<=1 favours REDACTION, >=2 favours DIAGNOSTICS; worst-case accuracy 0.87)")
    print("\n  This is a two-hypothesis discrimination, NOT a significance test.")
    print("  It does not restate F765 or F673, and 4687405^ carries every other")
    print("  pre-09-11 difference besides the two being separated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
