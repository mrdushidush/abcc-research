# -*- coding: utf-8 -*-
"""The DEBUG-P3 section 8 per-run table, for one sortie.

    python armrow.py t5430

Classifies every apply_patch refusal as MARKUP (F637's sentence, the server's
fold) or NOMATCH (F638's, a real diff that missed) and answers the one question
the arm exists for: did TWO MARKUP REFUSALS land BACK TO BACK, and if so did the
model then call write_file?
"""
import json, sqlite3, sys

DB = r"C:\Users\david\AppData\Local\abcc\abcc-1ae35b6091a63e2c\log.sqlite"

def classify(detail):
    d = detail or ""
    if "tool-call markup" in d:
        return "MARKUP"
    if "does not match" in d:
        return "NOMATCH"
    return "OTHER"

def main(task_id):
    c = sqlite3.connect("file:" + DB.replace("\\", "/") + "?mode=ro", uri=True)
    task = int(task_id.lstrip("t"))
    atts = [r[0] for r in c.execute("select id from attempt where task = ?", (task,))]
    marks = ",".join("?" * len(atts)) or "NULL"
    q = ("select seq, at_ms, kind, attempt, body from event "
         "where task = ? or attempt in (%s) order by seq" % marks)
    seen = list(c.execute(q, tuple([task] + atts)))
    if not seen:
        print("no events for %s" % task_id); return

    edits, endings = [], []
    for seq, at, kind, attempt, body in seen:
        b = json.loads(body) if body else {}
        if kind == "tool_call_ended" and b.get("tool") in ("apply_patch", "write_file"):
            un = b.get("unmeasured")
            detail = ""
            if isinstance(un, dict):
                detail = un.get("detail") or un.get("Denied") or json.dumps(un)[:300]
            edits.append((attempt, seq, b.get("tool"), bool(un), detail))
        elif kind == "attempt_ended":
            endings.append((attempt, json.dumps(b.get("outcome"))))

    print("=== %s ===" % task_id)
    tot = dict(ap=0, markup=0, nomatch=0, other=0, wf=0, wf_ref=0, b2b=0, wf_after_b2b=0)
    for att in atts:
        rows = [e for e in edits if e[0] == att]
        print("\n--- attempt a%s: %d edit call(s) ---" % (att, len(rows)))
        prev_markup = False
        armed_at = None
        for i, (_, seq, tool, refused, detail) in enumerate(rows, 1):
            kindstr = "ok"
            if tool == "apply_patch":
                tot["ap"] += 1
                if refused:
                    kindstr = classify(detail)
                    tot[kindstr.lower()] = tot.get(kindstr.lower(), 0) + 1
                    if kindstr == "MARKUP":
                        if prev_markup:
                            tot["b2b"] += 1
                            armed_at = seq
                            kindstr = "MARKUP  <<< BACK-TO-BACK, TRIGGER APPLICABLE"
                        prev_markup = True
                    else:
                        prev_markup = False
                else:
                    prev_markup = False
            else:  # write_file
                tot["wf"] += 1
                if refused:
                    tot["wf_ref"] += 1
                    kindstr = "REFUSED: " + detail[:120]
                if armed_at is not None:
                    tot["wf_after_b2b"] += 1
                    kindstr += "  <<< TOOK THE DOOR"
            print("  %2d. seq %-6s %-11s %s" % (i, seq, tool, kindstr))
            if refused and detail and tool == "apply_patch":
                print("        %s" % detail[:150].replace("\n", " "))

    print("\n--- endings ---")
    for att, o in endings:
        print("  a%s %s" % (att, o))

    print("\n--- the row ---")
    print("  apply_patch calls that ran     : %d" % tot["ap"])
    print("  refused for MARKUP (the fold)  : %d" % tot["markup"])
    print("  refused for NoMatch (near-miss): %d" % tot["nomatch"])
    print("  TWO MARKUP BACK TO BACK        : %s" % ("YES x%d" % tot["b2b"] if tot["b2b"] else "no"))
    print("  write_file called              : %d (refused %d)" % (tot["wf"], tot["wf_ref"]))
    print("  write_file AFTER the trigger   : %s" % ("YES x%d" % tot["wf_after_b2b"] if tot["wf_after_b2b"] else "no"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "t5221")
