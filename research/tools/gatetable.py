# -*- coding: utf-8 -*-
"""Did the tree change, and was the gate asked? One row per attempt, all five arms."""
import json, sqlite3, subprocess, os
DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"
ABCC = r"D:\dev\abcc"
c = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
ARMS = [("1*", 4886), ("2", 5221), ("3", 5430), ("4", 5683), ("5", 5871)]

def stat(a, b):
    r = subprocess.run(["git", "diff", "--shortstat", a, b], cwd=ABCC,
                       capture_output=True, text=True)
    return r.stdout.strip() or "(no change)"

print("%-4s %-8s %-11s %-34s %-6s %s" % ("arm", "attempt", "kind", "tree change", "gate", "ending"))
print("-" * 118)
n_changed = n_gated = 0
for arm, task in ARMS:
    ev = list(c.execute("select seq, kind, attempt, body from event where task = ? order by seq", (task,)))
    atts = [r[0] for r in c.execute("select id from attempt where task = ?", (task,))]
    # checkpoints in order: open_i, close_i, open_i+1, close_i+1 ...
    cps = [json.loads(b)["sha"] for s, k, a, b in ev if k == "checkpoint_taken"]
    opens = [json.loads(b)["sha"] for s, k, a, b in ev if k == "worktree_opened"]
    closes = []
    for i, o in enumerate(opens):
        j = cps.index(o)
        closes.append(cps[j + 1] if j + 1 < len(cps) else None)
    marks = ",".join("?" * len(atts))
    ends, gated, kinds = {}, set(), {}
    for seq, kind, att, body in c.execute(
        "select seq, kind, attempt, body from event where attempt in (%s) order by seq" % marks, atts):
        b = json.loads(body) if body else {}
        if kind == "attempt_ended":
            o = b.get("outcome") or {}
            ends[att] = o.get("why", {}).get("why") or ("REFUSED by " + str(o.get("rung")))
        elif kind == "rung_recorded":
            gated.add(att)
    for i, att in enumerate(atts):
        ch = stat(opens[i], closes[i]) if i < len(closes) and closes[i] else "?"
        changed = ch != "(no change)"
        n_changed += changed
        n_gated += att in gated
        print("%-4s a%-7s %-11s %-34s %-6s %s" % (
            arm, att, "fresh" if i == 0 else "retry", ch[:34],
            "ASKED" if att in gated else "—", ends.get(att, "?")))
print("-" * 118)
print("attempts that changed the tree: %d ; attempts the gate was asked about: %d" % (n_changed, n_gated))
