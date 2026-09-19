#!/usr/bin/env python3
r"""reviewpack.py - the morning review packet: every green attempt not yet landed.

  THIS EXISTS TO SPEND FEWER OF THE OPERATOR'S MINUTES, WHICH IS THE THING W13
MEASURES. M1's rung is *review minutes per merged change*, so a tool that puts
the diff, the rungs and the exact `land` command in one place is not a
convenience -- it moves the number the milestone is judged on. The first landing
cost 120 seconds; most of that is finding out what to look at.

  IT REFUSES TO GUESS TWO THINGS.
* Whether a diff still applies. Three of the four greens on this log went stale
  the moment `a0054e7` touched `seq.rs`, so every entry is test-applied against
  the CURRENT HEAD with `git apply --check` and says which way it went.
* Whether the rungs measured one tree. `land` rebuilds the report and asks
  `headline_at`, so a rung taken at a different sha is `StaleMeasurement` and
  the entitlement is `Unverified`. This reports the same thing up front rather
  than letting the operator find out from a refusal.

  AND IT NEVER LANDS AND NEVER REVIEWS. `abcc review` defaults `by` to
`operator()`, so an agent running it fabricates the measurement SELF-HOST is
judged on. This prints the command; a person types it.

Read-only. Nothing here writes to the log or to the repository.

Usage:
    reviewpack.py                 # every unlanded green, newest first
    reviewpack.py --diff          # include the full diff of each
    reviewpack.py --task t13051   # just one
"""

import argparse
import json
import pathlib
import sqlite3
import subprocess
import sys

DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"
REPO = r"D:\dev\abcc"


def git(*args):
    """Text mode, for output a human reads."""
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True,
                       text=True, errors="replace")
    return r.returncode, r.stdout, r.stderr


def git_bytes(*args, stdin=None):
    r"""BYTES, and that is the whole point of having two of these.

      🚨 A PATCH MUST NEVER GO THROUGH PYTHON TEXT MODE ON WINDOWS.
    `subprocess.run(text=True, input=patch)` writes the string through a
    TextIOWrapper, which translates every `
` to `
` on the way into the
    child -- so `git apply --check` was handed a CRLF patch for an LF tree and
    reported `patch failed: crates/abcc/src/main.rs:13` on a patch that applies
    cleanly through a shell pipe. The conflict was Python's, not git's.
    """
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, input=stdin)
    return r.returncode, r.stdout, r.stderr


def rows(db):
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    ev = [(s, a, t, ms, json.loads(b)) for s, a, t, ms, b in
          con.execute("select seq, attempt, task, at_ms, body from event order by seq")]
    titles = {t: (ti, p) for t, ti, p in
              con.execute("select id, title, prompt from task")}
    return ev, titles


def greens(ev, near=False):
    """Every attempt that ended `success`, with the trees it ran between.

    With `near`, also the attempts REFUSED at a rung while the others measured.

      THE NEAR-MISSES ARE WHY THIS FLAG EXISTS. t13051's first attempt added
    `Seq::back` correctly -- structural green, veto green, **681 of 681 tests
    passed** -- and `clippy::manual_let_else` refused it, which is a style lint
    and not the substance. A refusal is a MEASURED ANSWER rather than a failure,
    so the engine hands it to the operator and never retries it (ADR-0009), and
    the task sits at INTERVENTION REQUIRED. A change one line from landing is
    worth putting in front of a person; the alternative is reading five runs as
    five losses.
    """
    landed = {e["task"] for _, _, _, _, e in ev if e["kind"] == "change_landed"}
    out = []
    for seq, att, task, ms, e in ev:
        if e["kind"] != "attempt_ended":
            continue
        oc = (e.get("outcome") or {}).get("outcome")
        if oc != "success" and not (near and oc == "refused"):
            continue
        #   TWO THINGS ABOUT THE PAIR, AND THE FIRST DRAFT GOT BOTH WRONG.
        # (1) The attempt id IS the seq of its `attempt_started` (ADR-0005:
        # identity is the position of the event that created it), which is why
        # that event carries no `attempt` field to look up.
        # (2) 🚨 **The OPENING checkpoint is taken BEFORE `attempt_started`** --
        # a2137 opened on the snapshot at seq 2135 and started at 2137 -- because
        # the worktree is opened at a tree and only then does the attempt begin.
        # Bracketing `start <= s` therefore dropped every `from` and reported
        # "no checkpoint pair on the log" for five attempts that all had one.
        # `land.rs` calls it "the checkpoint the attempt opened on"; it is the
        # LAST one at or before the start.
        mine = [(s, x) for s, _, t2, _, x in ev
                if x["kind"] == "checkpoint_taken" and t2 == task and s <= seq]
        opening = [x for s, x in mine if s <= att]
        closing = [x for s, x in mine if s > att]
        cps = ([opening[-1]] if opening else []) + ([closing[-1]] if closing else [])
        rungs = [x["outcome"] for _, a2, _, _, x in ev
                 if x["kind"] == "rung_recorded" and a2 == att]
        out.append({
            "attempt": att, "task": task, "seq": seq, "outcome": oc,
            "refused_rung": (e.get("outcome") or {}).get("rung"),
            "from": cps[0].get("sha") if cps else None,
            "to": cps[-1].get("sha") if len(cps) > 1 else None,
            "rungs": rungs, "landed": task in landed,
        })
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--diff", action="store_true")
    p.add_argument("--task")
    p.add_argument("--all", action="store_true", help="landed ones too")
    p.add_argument("--near", action="store_true",
                   help="also attempts refused at a rung with the others green")
    args = p.parse_args()

    if not pathlib.Path(REPO).exists():
        sys.exit(f"no repository at {REPO}")
    _, head, _ = git("rev-parse", "--short", "HEAD")
    _, dirty, _ = git("status", "--porcelain")
    ev, titles = rows(DB)

    print()
    print(f"REVIEW PACKET   HEAD {head.strip()}   "
          f"working tree {'DIRTY - land will refuse' if dirty.strip() else 'clean'}")

    found = [g for g in greens(ev, near=args.near) if args.all or not g["landed"]]
    if args.task:
        want = int(args.task.lstrip("t"))
        found = [g for g in found if g["task"] == want]
    if not found:
        print()
        print("Nothing green and unlanded. Either everything is merged or nothing")
        print("has gone green yet -- `abcc board` says which.")
        return 0

    for g in sorted(found, key=lambda x: -x["seq"]):
        title, prompt = titles.get(g["task"], (None, ""))
        print()
        print("=" * 78)
        tag = "   [ALREADY LANDED]" if g["landed"] else ""
        if g["outcome"] == "refused":
            tag += f"   [NEAR MISS - refused at the {g['refused_rung']} rung]"
        print(f"t{g['task']}  a{g['attempt']}   {title or '(untitled)'}{tag}")
        print("=" * 78)
        print(f"  asked: {' '.join((prompt or '').split())[:300]}")

        # The rungs, and whether they all name the tree being landed.
        shas = {r.get("sha") for r in g["rungs"]}
        allgreen = all(r.get("exit") == 0 and r.get("outcome") == "measured"
                       for r in g["rungs"])
        onetree = len(shas) == 1 and g["to"] in shas
        print(f"  rungs: {len(g['rungs'])}  all green: {allgreen}  "
              f"all at the landed tree: {onetree}")
        for r in g["rungs"]:
            c = r.get("counts")
            tests = f"  tests {c['passed']}/{c['run']}" if c else ""
            print(f"           {r.get('rung', '?'):11} exit={r.get('exit')}{tests}")
        if g["outcome"] == "refused":
            red = [r for r in g["rungs"] if r.get("exit") not in (0, None)]
            print(f"  !! NOT LANDABLE: {len(red)} of {len(g['rungs'])} rung(s) refused.")
            for r in red:
                for line in str(r.get("detail", "")).splitlines()[:7]:
                    print(f"       {line}")
        elif not (allgreen and onetree):
            print("  !! `land` will refuse or downgrade this - the entitlement is")
            print("     Headline::Green over rungs that all name one tree.")

        if not (g["from"] and g["to"]):
            print("  !! no checkpoint pair on the log; nothing to apply.")
            continue

        code, patch, err = git_bytes("diff", g["from"], g["to"])
        if code != 0:
            print("  !! the checkpoint pair is no longer readable: "
                  f"{err.decode('utf-8', 'replace').strip()[:120]}")
            continue
        _, stat, _ = git("diff", "--stat", g["from"], g["to"])
        for line in stat.rstrip().splitlines():
            print(f"  {line}")

        ok, _, aerr = git_bytes("apply", "--check", "-", stdin=patch)
        aerrs = aerr.decode("utf-8", "replace").strip()
        if ok == 0:
            print(f"  APPLIES CLEANLY to {head.strip()}")
        else:
            print(f"  CONFLICTS with {head.strip()} - {aerrs.splitlines()[0][:100]}"
                  if aerrs else f"  CONFLICTS with {head.strip()}")
            print("     (`land` uses `git apply --3way`, which reconstructs the")
            print("      pre-image from the blobs, so it may still succeed)")

        if args.diff:
            print()
            for line in patch.decode("utf-8", "replace").rstrip().splitlines():
                print(f"    {line}")

        print()
        if g["outcome"] == "refused":
            print("  `land` will refuse this - the gate did. Either finish it by")
            print("  hand (the diff above is the work, the rung output says what is")
            print(f"  left), or stop it:  abcc reject {g['task']}")
        else:
            print(f"  to land it:   .\\target\\release\\abcc.exe land {g['task']}")
            print("  then:         .\\target\\release\\abcc.exe review <sha> <minutes>")

    print()
    print(f"{len(found)} change(s) waiting. `land` and `review` are the operator's:")
    print("`by` defaults to operator(), so an agent running review fabricates the")
    print("measurement SELF-HOST is judged on.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
