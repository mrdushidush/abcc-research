"""One row per attempt: the H1 record, read-only from the claudette log."""
import json
import sqlite3
import sys
from collections import Counter

DB = "file:C:/Users/david/AppData/Local/abcc/claudette-92490a1b1de94eca/log.sqlite?mode=ro"
con = sqlite3.connect(DB, uri=True)
EDITORS = ("edit_file", "write_file", "apply_patch")

print("| attempt | task | ending | tool calls | editing calls | read_file calls | read bytes | prompt tokens | wall |")
print("|---|---|---|---:|---|---:|---:|---:|---:|")
for a in [int(x.lstrip("a")) for x in sys.argv[1:]]:
    task, outcome = con.execute("select task, outcome from attempt where id=?", (a,)).fetchone()
    rows = con.execute("select at_ms, kind, body from event where attempt=? order by seq", (a,)).fetchall()
    started = [json.loads(b) for _, k, b in rows if k == "tool_call_started"]
    ended = [json.loads(b) for _, k, b in rows if k == "tool_call_ended"]
    tools = Counter(b["tool"] for b in started)
    edits = {t: tools[t] for t in EDITORS if tools[t]}
    applied = Counter(b["tool"] for b in ended if b["tool"] in EDITORS and not b.get("unmeasured"))
    edit_s = ", ".join(f"{t} {n} ({applied[t]} ok)" for t, n in edits.items()) or "0"
    rb = sum(len((b.get("output") or "").encode("utf-8")) for b in ended if b["tool"] == "read_file")
    prompt = sum(json.loads(b).get("prompt_tokens", 0) for _, k, b in rows if k == "phase_ended")
    wall = (rows[-1][0] - rows[0][0]) / 1000 if rows else 0
    o = json.loads(outcome) if outcome else {"outcome": "running"}
    ending = o["outcome"] + ("/" + o["why"]["why"] if isinstance(o.get("why"), dict) else "")
    print(f"| a{a} | t{task} | {ending} | {sum(tools.values())} | {edit_s} | {tools['read_file']} | {rb:,} | {prompt:,} | {wall:.0f} s |")
