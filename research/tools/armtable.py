# -*- coding: utf-8 -*-
"""The whole E0004 subject in one table: every arm, every attempt."""
import json, sqlite3, sys
DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"
c = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)

ARMS = [("arm 1 (pre-F649)", 4886), ("arm 2", 5221), ("arm 3", 5430),
        ("arm 4", 5683), ("arm 5", 5871),
        ("arm 6 (F655)", 6207)]

def cls(d):
    d = d or ""
    if "tool-call markup" in d: return "MARKUP"
    if "does not match" in d: return "NOMATCH"
    return "OTHER"

tot = dict(ap=0, mk=0, nm=0, ok=0, wf=0, b2b=0, first_mk=0, first_any=0)
print("%-18s %-8s %-7s %-30s %s" % ("arm", "attempt", "ap", "apply_patch sequence", "ending"))
print("-" * 110)
for name, task in ARMS:
    atts = [r[0] for r in c.execute("select id from attempt where task = ?", (task,))]
    if not atts:
        print("%-18s (not flown yet)" % name); continue
    marks = ",".join("?" * len(atts))
    ev = list(c.execute(
        "select seq, kind, attempt, body from event where (task = ? or attempt in (%s)) "
        "order by seq" % marks, tuple([task] + atts)))
    per = {}
    end = {}
    for seq, kind, att, body in ev:
        b = json.loads(body) if body else {}
        if kind == "tool_call_ended" and b.get("tool") in ("apply_patch", "write_file"):
            un = b.get("unmeasured")
            det = un.get("detail") if isinstance(un, dict) else ""
            per.setdefault(att, []).append((b["tool"], cls(det) if un else "ok"))
        elif kind == "attempt_ended":
            o = b.get("outcome") or {}
            end[att] = o.get("why", {}).get("why") or o.get("rung") or o.get("outcome")
    for att in atts:
        calls = per.get(att, [])
        ap = [k for t, k in calls if t == "apply_patch"]
        wf = [k for t, k in calls if t == "write_file"]
        seqstr = " ".join(("mk" if k == "MARKUP" else "nm" if k == "NOMATCH" else
                           "OK" if k == "ok" else "??") for k in ap) or "—"
        tot["ap"] += len(ap); tot["mk"] += ap.count("MARKUP")
        tot["nm"] += ap.count("NOMATCH"); tot["ok"] += ap.count("ok")
        tot["wf"] += len(wf)
        tot["b2b"] += sum(1 for i in range(1, len(ap))
                          if ap[i] == "MARKUP" and ap[i-1] == "MARKUP")
        if ap:
            tot["first_any"] += 1
            if ap[0] == "MARKUP": tot["first_mk"] += 1
        print("%-18s a%-7s %-7d %-30s %s" % (name, att, len(ap), seqstr, end.get(att, "?")))

print("-" * 110)
print("apply_patch calls           : %d" % tot["ap"])
print("  refused MARKUP (the fold)  : %d" % tot["mk"])
print("  refused NoMatch            : %d" % tot["nm"])
print("  succeeded                  : %d" % tot["ok"])
print("write_file calls             : %d" % tot["wf"])
print("two MARKUP back to back      : %d" % tot["b2b"])
print("attempts whose FIRST apply_patch was MARKUP: %d of %d" % (tot["first_mk"], tot["first_any"]))
