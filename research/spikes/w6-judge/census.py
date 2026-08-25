#!/usr/bin/env python3
"""W6 item 7 — OQ-W6-13: what the 29 clean-arm failures actually are.

F321 left the question open: on the 280 Q56 cells where nothing interfered with
the agent, 29 attempts are real failures and not one deterministic rung in five
languages goes red on any of them. K's taxonomy (F302) does not transfer, because
these are one-file tasks where the file was always written.

This dumps the material for a hand classification — the ticket, the fixture the
agent started from, the tree it left, the reference solution, and the assertion
the hidden reviewer test failed on — and nothing here is a model's opinion.

    python census.py > census-out.txt
"""

from __future__ import annotations

import difflib
import pathlib
import re
import sys

import common as C

HERE = pathlib.Path(__file__).resolve().parent


def unified(a: dict) -> str:
    out = []
    for path in a["changed"]:
        before = a["fixture"].get(path, "")
        after = a["files"].get(path, "")
        out.append("".join(difflib.unified_diff(
            before.splitlines(True), after.splitlines(True),
            fromfile=f"fixture/{path}", tofile=f"work/{path}", n=3)))
    for path in a["added"]:
        if path not in a["changed"]:
            out.append(f"+++ work/{path} (new file, {len(a['files'][path])} chars)\n")
    return "".join(out)


HEREDOC = re.compile(
    r"cat > (?P<path>\S+) <<'(?P<tag>RS|PY|JS|TS)'\n(?P<body>.*?)\n(?P=tag)\n",
    re.S)


def hidden_asserts(task: str) -> str:
    """The hidden reviewer tests the verifier writes at grade time.

    They live in heredocs inside `verify.sh` (four tags across the suite: RS, PY,
    JS, TS) and are written into the workdir only while grading, so the subject
    never sees them. Shell tasks have no heredoc — their checks are inline — so
    those fall back to the assertion-ish lines of the script.
    """
    src = C.hidden_tests(task)
    blocks = [f"--- {m.group('path')} ---\n{m.group('body')}"
              for m in HEREDOC.finditer(src)]
    if blocks:
        return "\n".join(blocks)
    body = src.split('cd "$WORKDIR"', 1)[-1]
    keep = [l.rstrip() for l in body.splitlines()
            if re.search(r"expected|got |fail |-eq |\[\[|assert", l)
            and not l.strip().startswith("#")]
    return "\n".join(keep)


def main():
    # The corpus is UTF-8 (em dashes in every ticket, `->` in one diff) and this
    # console is cp1252, so a shell redirect dies mid-dump with a charmap error
    # and truncates the census where it happens to be. Write the file directly,
    # utf-8, LF — the same trap the memory file records twice.
    out = HERE / "census-out.txt"
    fh = out.open("w", encoding="utf-8", newline="\n")
    sys.stdout = fh

    pop = [a for a in C.population() if a["truth"] == "FAIL"]
    pop.sort(key=lambda a: (a["task"], a["content_sha"]))
    print(f"# {len(pop)} unique failing trees over "
          f"{sum(a['n_cells'] for a in pop)} cells, "
          f"{len({a['task'] for a in pop})} distinct tasks\n")
    for a in pop:
        print("=" * 78)
        print(f"{a['task']}  {a['lang']}  sha={a['content_sha']}  "
              f"cells={a['n_cells']}  {a['uids'][0]}")
        print(f"VERDICT: {a['truth_line']}")
        print("-" * 78)
        print("TICKET:")
        print(C.ticket(a["task"]))
        print("-" * 78)
        print("WHAT THE AGENT CHANGED:")
        print(unified(a))
        print("-" * 78)
        print("REFERENCE SOLUTION:")
        for p, t in sorted(C.refsol(a["task"]).items()):
            print(f"--- refsol/{p} ---")
            print(t)
        print("-" * 78)
        print("HIDDEN ASSERTIONS (answer key, never shown to a model):")
        print(hidden_asserts(a["task"]))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
