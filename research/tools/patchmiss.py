#!/usr/bin/env python3
"""How close did a refused `apply_patch` come, and what did the message say?

F505 keeps a failed tool call's arguments on the log, so every refused diff is
recoverable after the fact. This reads them back, finds the position in the
target file where the *most* context lines match, and reports the first line
that differs — which is the question `PatchError::NoMatch` does not answer.

The point is to separate two very different failures that produce one message:

  * the model invented context that is nowhere in the file  (a real miss)
  * the model got one line slightly wrong                   (a near miss)

⚠ The file is read from the operator's checkout at HEAD, not from the worktree
the attempt actually ran in — that tree is removed when the attempt lands. They
are the same tree except for anything committed since, so a near-miss count is
a floor rather than an exact figure.

    python patchmiss.py --log <path> --repo <path> [--since <seq>]
"""
import argparse
import json
import os
import re
import sqlite3

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def hunks(diff: str):
    """(path, claimed_line, [expected lines]) for every hunk in the diff."""
    out, path, claimed, expects, want = [], None, None, None, None
    for line in diff.split("\n"):
        if line.startswith("--- "):
            if expects is not None:
                out.append((path, claimed, expects))
                expects = None
            continue
        if line.startswith("+++ "):
            path = line[4:].strip()
            for prefix in ("a/", "b/"):
                if path.startswith(prefix):
                    path = path[2:]
            continue
        m = HUNK.match(line)
        if m:
            if expects is not None:
                out.append((path, claimed, expects))
            claimed, expects = int(m.group(1)), []
            # How many old-file lines this hunk covers. Absent means 1, per the
            # unified-diff format.
            want = int(m.group(2)) if m.group(2) is not None else 1
            continue
        if expects is None:
            continue
        # 🚨 The header's old-file count is authoritative, and honouring it is not
        # tidiness. Without it, the trailing empty string that `split("\n")`
        # produces was collected as a context line, so the LAST hunk of every diff
        # carried a phantom blank line that matched nothing — and the first run of
        # this tool reported "the model wrote a blank line" as 64% of all
        # single-line misses. 82 of those 85 sat at the last line of their hunk,
        # which is what gave it away. The finding was the instrument.
        if want is not None and len(expects) >= want:
            continue
        # Context and removals are what has to already be in the file.
        if line.startswith((" ", "-")):
            expects.append(line[1:])
        elif line.startswith("+"):
            pass
        elif line == "":
            expects.append("")
    if expects is not None:
        out.append((path, claimed, expects))
    return [h for h in out if h[2]]


def best_match(lines, expects):
    """The offset where the most expected lines match, and how many."""
    best, at = -1, None
    span = len(expects)
    for start in range(0, max(1, len(lines) - span + 1)):
        hit = sum(
            1
            for i, want in enumerate(expects)
            if start + i < len(lines) and lines[start + i].rstrip("\r") == want.rstrip("\r")
        )
        if hit > best:
            best, at = hit, start
    return at, best


def first_difference(lines, expects, at):
    for i, want in enumerate(expects):
        got = lines[at + i] if at + i < len(lines) else "<past end of file>"
        if got.rstrip("\r") != want.rstrip("\r"):
            return i, want, got
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--since", type=int, default=0)
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.log}?mode=ro", uri=True)
    rows = [
        json.loads(b)
        for (b,) in c.execute("SELECT body FROM event WHERE seq > ? ORDER BY seq", (a.since,))
    ]

    refused = [
        e
        for e in rows
        if e["kind"] == "tool_call_ended"
        and e.get("tool") == "apply_patch"
        and e.get("arguments")
        and e.get("unmeasured")
    ]
    print(f"refused apply_patch calls with arguments on the log: {len(refused)}\n")

    near, real, unreadable = 0, 0, 0
    for n, e in enumerate(refused, 1):
        detail = e["unmeasured"].get("detail", "")
        try:
            diff = json.loads(e["arguments"])["diff"]
        except Exception:
            unreadable += 1
            continue
        print(f"--- call {n}: {detail[:110]}")
        for path, claimed, expects in hunks(diff):
            full = os.path.join(a.repo, path.replace("/", os.sep))
            if not os.path.exists(full):
                print(f"    {path}: not in the checkout")
                continue
            lines = open(full, encoding="utf-8", errors="replace").read().split("\n")
            at, hit = best_match(lines, expects)
            miss = first_difference(lines, expects, at)
            if hit == len(expects):
                continue  # this hunk would apply; another one failed
            verdict = "NEAR MISS" if hit >= len(expects) - 2 else "real miss"
            if hit >= len(expects) - 2:
                near += 1
            else:
                real += 1
            print(
                f"    {path} hunk@{claimed}: {hit}/{len(expects)} context lines match "
                f"at line {at + 1} -> {verdict}"
            )
            if miss:
                i, want, got = miss
                print(f"      first difference, expected line {i + 1} of the hunk:")
                print(f"        model: {want!r}")
                print(f"        file : {got!r}")
        print()

    total = near + real
    if total:
        print(f"SUMMARY: {near}/{total} failing hunks are NEAR MISSES "
              f"(all but <=2 context lines matched), {real} are real misses")
