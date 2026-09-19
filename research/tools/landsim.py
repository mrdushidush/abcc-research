#!/usr/bin/env python3
r"""landsim.py - does the SECOND landing still apply after the FIRST one commits?

  THIS ANSWERS A QUESTION THE LAST SESSION REPORTED AS UNKNOWN, AND SAID WHY.
`reviewpack.py` test-applies every green diff against the CURRENT head, which
answers "would `land` take this one". It does not answer "would `land` take all
four, one after another", because after the first commit the tree has moved and
the remaining three have never been measured against it. The previous attempt at
this applied the patches to the WORKING TREE without committing, so git's
`does not match index` was an artifact of the test rig rather than a verdict on
`land` -- answering it properly needs commits, and commits on `main` are
`abcc land`, which is the operator's.

  SO IT COMMITS SOMEWHERE ELSE. A detached `git worktree` at the current HEAD
has the whole object store and its own index, so the four applies can be
performed for real, in order, with a real commit between each -- and `main` is
never touched. The worktree is removed at the end, and `--keep` is the only way
to leave one behind.

  IT REPRODUCES `land`'s MECHANISM RATHER THAN APPROXIMATING IT.
* the pair is the attempt's own `checkpoint_taken` shas (`land.rs::landing`),
  newest green attempt first;
* the patch is `git diff --no-ext-diff --no-color --find-renames --unified=3`
  (`Repo::patch_between`), byte for byte the pre-image the Judge was shown;
* the apply is `git apply --index --3way` (`Repo::apply`), which is the line
  that matters: `--3way` reconstructs the pre-image from the blobs, so a diff
  taken against an older tree can still land.
A pass here is not a promise that `abcc land` will succeed -- `land` also checks
the entitlement and refuses a dirty checkout -- but the apply is the only step
that a preceding landing can break, and this is that step.

  WHAT IT REFUSES TO DO. It never writes to the log, never touches `main`, and
never runs `land` or `review`. It prints the order a person types.

Usage:
    landsim.py                        # the four, in the recommended order
    landsim.py t13606 t14016 t13604   # a different order
    landsim.py --gate                 # also run the four rung commands at the end
    landsim.py --keep                 # leave the worktree for inspection
"""

import argparse
import pathlib
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from reviewpack import DB, REPO, greens, rows  # noqa: E402

#   THE ORDER, AND THE ONE REASON IT IS NOT ARBITRARY. t13055 `Seq::forward`
# and t13606 `Seq::back` both insert at the same point in `impl Seq` AND both
# add a `#[cfg(test)] mod tests` to a `seq.rs` that has none, so landing both
# gives two modules of one name -- E0428, a compile error rather than a merge
# conflict. t13606 is preferred (5 tests against 2), so t13055 is left out and
# re-run against the landed tree.
DEFAULT = ["t14016", "t13604", "t13606", "t8319"]

#   The gate's own commands, read out of `TOOLCHAINS` in
# `crates/abcc-engine/src/workspace.rs:196` rather than from any prose about it.
GATE = [
    ["cargo", "check", "--all-targets"],
    ["cargo", "test"],
    ["cargo", "fmt", "--check", "--", "--color=never"],
    ["cargo", "clippy", "--all-targets", "--", "-D", "warnings"],
]


def git(cwd, *args, stdin=None):
    r"""BYTES in and BYTES out, for the reason `reviewpack.py` learned the hard
    way: a patch through Python's text mode gets every `\n` translated on the
    way into the child, and git then reports a confident line-numbered conflict
    that is Python's rather than git's."""
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, input=stdin)
    return r.returncode, r.stdout, r.stderr


def text(b):
    return b.decode("utf-8", "replace").strip()


def pairs(tasks):
    """The (from, to) checkpoint pair for each named task's landable attempt."""
    ev, titles = rows(DB)
    landed = {g["task"] for g in greens(ev) if g["landed"]}
    by_task = {}
    #   Newest attempt first and the first green one wins -- `land.rs::landing`
    # says why: a retried task forked from the earlier attempt's checkpoint, so
    # landing the older green would land a tree the project has moved past.
    for g in sorted(greens(ev), key=lambda x: -x["seq"]):
        by_task.setdefault(g["task"], g)
    out = []
    for t in tasks:
        n = int(t.lstrip("t"))
        g = by_task.get(n)
        if g is None:
            sys.exit(f"{t} has no green attempt on the log")
        if n in landed:
            sys.exit(f"{t} is already landed; landing it twice is two commits of one change")
        if not (g["from"] and g["to"]):
            sys.exit(f"{t} has no checkpoint pair on the log, so there is nothing to apply")
        out.append((t, titles.get(n, ("(untitled)", ""))[0], g))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tasks", nargs="*", default=None)
    p.add_argument("--gate", action="store_true", help="run the four rung commands at the end")
    p.add_argument("--keep", action="store_true", help="leave the worktree behind")
    p.add_argument("--at", default="HEAD", help="the tree to start from (default: HEAD)")
    args = p.parse_args()

    tasks = args.tasks or DEFAULT
    plan = pairs(tasks)

    code, head, _ = git(REPO, "rev-parse", args.at)
    if code != 0:
        sys.exit(f"cannot resolve {args.at}")
    head = text(head)
    _, short, _ = git(REPO, "rev-parse", "--short", head)

    wt = pathlib.Path(REPO).parent / f"abcc-landsim-{text(short)}"
    if wt.exists():
        sys.exit(f"{wt} already exists -- remove it first (`git worktree remove`)")

    print()
    print(f"LANDING SIMULATION   from {text(short)}   {len(plan)} change(s), in this order")
    print(f"  worktree  {wt}")
    print("  main is never touched; every commit below is made on a detached HEAD.")

    code, _, err = git(REPO, "worktree", "add", "--detach", str(wt), head)
    if code != 0:
        sys.exit(f"could not make the worktree: {text(err)}")

    results = []
    try:
        for i, (t, title, g) in enumerate(plan, 1):
            print()
            print("=" * 78)
            print(f"{i}. {t}  a{g['attempt']}   {title}")
            print("=" * 78)
            code, patch, err = git(REPO, "diff", "--no-ext-diff", "--no-color",
                                   "--find-renames", "--unified=3", g["from"], g["to"])
            if code != 0:
                print(f"   !! the checkpoint pair is not readable: {text(err)[:150]}")
                results.append((t, "unreadable pair"))
                break
            _, stat, _ = git(REPO, "diff", "--stat", g["from"], g["to"])
            for line in text(stat).splitlines():
                print(f"   {line}")

            #   The plain applier first, purely so the report can say WHICH of
            # the two succeeded. `land` only ever runs the --3way form; a patch
            # that needs the fallback is still a landing, just not a trivial one.
            plain, _, _ = git(wt, "apply", "--check", "-", stdin=patch)
            code, _, err = git(wt, "apply", "--index", "--3way", "-", stdin=patch)
            if code != 0:
                print(f"   !! APPLY FAILED: {text(err)[:400]}")
                results.append((t, "apply failed"))
                break
            how = "cleanly" if plain == 0 else "via the --3way fallback"
            print(f"   applied {how}")

            code, _, err = git(wt, "-c", "user.name=landsim", "-c", "user.email=landsim@localhost",
                               "commit", "-m", f"landsim: {title} ({t})")
            if code != 0:
                print(f"   !! COMMIT FAILED: {text(err)[:300]}")
                results.append((t, "commit failed"))
                break
            _, sha, _ = git(wt, "rev-parse", "--short", "HEAD")
            print(f"   committed {text(sha)}")
            results.append((t, f"ok ({how})"))

        gate = []
        if args.gate and all(r[1].startswith("ok") for r in results) and len(results) == len(plan):
            print()
            print("=" * 78)
            print("THE GATE, over the tree all of them made")
            print("=" * 78)
            for cmd in GATE:
                r = subprocess.run(cmd, cwd=wt, capture_output=True)
                tail = text(r.stderr).splitlines()[-1:] or text(r.stdout).splitlines()[-1:]
                print(f"   exit {r.returncode:<3} {' '.join(cmd)}")
                if r.returncode != 0:
                    for line in (text(r.stdout) + "\n" + text(r.stderr)).splitlines()[-25:]:
                        print(f"        {line}")
                elif tail:
                    print(f"        {tail[0][:100]}")
                gate.append((" ".join(cmd), r.returncode))
    finally:
        if not args.keep:
            subprocess.run(["git", "-C", REPO, "worktree", "remove", "--force", str(wt)],
                           capture_output=True)
            shutil.rmtree(wt, ignore_errors=True)
            subprocess.run(["git", "-C", REPO, "worktree", "prune"], capture_output=True)

    print()
    print("-" * 78)
    for t, how in results:
        print(f"   {t:<8} {how}")
    ok = len(results) == len(plan) and all(h.startswith("ok") for _, h in results)
    if args.gate:
        ok = ok and all(c == 0 for _, c in gate)
    print()
    if ok:
        print("THE ORDER HOLDS. In the operator's own hand, one at a time:")
        for t in tasks:
            print(f"   .\\target\\release\\abcc.exe land {t.lstrip('t')}")
            print("   .\\target\\release\\abcc.exe review <sha it prints> <minutes>")
    else:
        print("THE ORDER DOES NOT HOLD -- see the failure above. Nothing was landed.")
    print()
    print("`land` and `review` are the operator's. `by` defaults to operator(),")
    print("so an agent running review fabricates the measurement SELF-HOST is judged on.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
