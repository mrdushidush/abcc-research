# -*- coding: utf-8 -*-
"""What an attempt did: every tool call in order, and what the refusals said.

    python research/tools/sortieread.py t5221

Written for DEBUG-P3's F649 arm and kept because the next arm needs it. Reads
the log READ-ONLY; nothing here writes.

TWO TRAPS THIS TOOL WAS BORN FROM -- both produced confident wrong numbers, and
both were caught only by running against t4886, whose answer is published in
CONSOLE-P10 section 13:

  * `tool_call_ended` carries `attempt` and a **NULL `task`**. A query keyed on
    the task returns the lifecycle rows and NONE of the work -- it reported zero
    tool calls for an attempt that made 42, which is a plausible thing for a
    failed attempt to have done.
  * `attempt.started` / `attempt.ended` are **seq numbers, not milliseconds**.
    Differenced they give durations of 0.2 s. Use `event.at_ms`.

WHAT TO READ OUT OF IT, for the F650 arm:
  1. how many `apply_patch` calls ran, and how many were refused for MARKUP
     (F637's sentence) rather than for `NoMatch` (F638's);
  2. whether TWO MARKUP REFUSALS EVER LANDED BACK TO BACK -- that, and only
     that, is what makes F649's `write_file` offer applicable;
  3. whether `write_file` was ever called;
  4. the ending of each attempt, which has varied every single run.
"""
import json
import sqlite3
import sys

DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"


def conn():
    return sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)


def rows(c, task):
    """Events for the task AND for every attempt of it.

    tool_call_ended carries `attempt` and a NULL `task`, so a query on `task`
    alone returns the lifecycle and none of the work -- which is how the first
    version of this reader reported zero tool calls on an attempt that made
    twenty-seven. Validated against t4886, whose answer is known.
    """
    atts = [r[0] for r in c.execute("select id from attempt where task = ?", (task,))]
    marks = ",".join("?" * len(atts)) or "NULL"
    q = ("select seq, at_ms, kind, attempt, body from event "
         "where task = ? or attempt in (%s) order by seq" % marks)
    return list(c.execute(q, tuple([task] + atts)))


def main(task_id):
    c = conn()
    task = int(task_id.lstrip("t"))
    seen = rows(c, task)
    if not seen:
        print("no events for %s" % task_id)
        return

    print("=== %s — %d events ===" % (task_id, len(seen)))
    order = []          # (attempt, tool, refused?, detail)
    endings = []
    phases = []
    for seq, at, kind, attempt, body in seen:
        b = json.loads(body) if body else {}
        if kind == "tool_call_ended":
            un = b.get("unmeasured")
            detail = ""
            if isinstance(un, dict):
                detail = un.get("detail") or un.get("Denied") or json.dumps(un)[:200]
            order.append((attempt, b.get("tool"), bool(un), detail, seq))
        elif kind == "phase_ended":
            phases.append((attempt, b.get("phase"), json.dumps(b.get("ended"))[:220]))
        elif kind in ("attempt_ended", "task_transitioned", "rung_recorded", "gate_recorded"):
            endings.append((seq, kind, attempt, json.dumps(b)[:300]))

    # The tool sequence, per attempt.
    for att in sorted({o[0] for o in order}):
        calls = [o for o in order if o[0] == att]
        print("\n--- attempt a%s: %d tool calls ---" % (att, len(calls)))
        counts = {}
        for _, tool, refused, _, _ in calls:
            k = (tool, refused)
            counts[k] = counts.get(k, 0) + 1
        for (tool, refused), n in sorted(counts.items()):
            print("   %-14s %s  x%d" % (tool, "REFUSED" if refused else "ok     ", n))

        # The edit tools in order, which is the whole question.
        edits = [o for o in calls if o[1] in ("apply_patch", "write_file")]
        if edits:
            print("   edit-tool sequence:")
            for i, (_, tool, refused, detail, seq) in enumerate(edits, 1):
                mark = "REFUSED" if refused else "OK"
                print("     %2d. seq %-6s %-11s %s" % (i, seq, tool, mark))
                if refused and detail:
                    print("         %s" % detail[:300].replace("\n", " "))

    print("\n--- phases ---")
    for att, phase, ended in phases:
        print("  a%s %-9s %s" % (att, phase, ended))

    print("\n--- endings / gate ---")
    for seq, kind, att, b in endings:
        print("  %-6s %-18s a%-6s %s" % (seq, kind, att, b))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "t5221")
