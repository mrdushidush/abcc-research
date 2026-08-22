"""W11 item 5 — replay ABCC v1's per-path tool limits over every measured run.

v1's ActionHistory (packages/agents/src/monitoring/action_history.py:15-19) caps
tool calls per target path, cumulatively, for the whole task:

    file_write: 3   file_edit: 5   shell_run: 10 (same command)

The transcripts here narrate mutations only (F91), so writes and edits are exactly
the two limits that can be replayed faithfully: they are keyed on path and counted
cumulatively, so unnarrated reads in between cannot change the count.

Mapping: claudette `write_file` -> v1 `file_write` (cap 3)
         claudette `apply_diff` / `edit_file` / `apply_patch` -> v1 `file_edit` (cap 5)

Also replays the window rule that CAN be checked one-sided: "same tool 5+ times in
the last 5 actions" — reported as a run of >=5 consecutive narrated mutations of the
same verb. Unnarrated tool calls could interrupt such a run, so this arm is an
UPPER bound on firings, and is labelled as such.
"""
import json, glob, os, re, collections

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
LINE = re.compile(r"▸ (write_file|apply_diff|edit_file|apply_patch): (.+?) \((?:new|\d+ →)")
V1 = {"write_file": ("file_write", 3), "apply_diff": ("file_edit", 5),
      "edit_file": ("file_edit", 5), "apply_patch": ("file_edit", 5)}

# index cells by their transcript path
cells = {}
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "**", "cells.jsonl"), recursive=True)):
    base = os.path.dirname(f)
    for line in open(f, encoding="utf-8"):
        if not line.strip(): continue
        c = json.loads(line)
        t = c.get("transcript")
        if not t: continue
        p = os.path.normpath(os.path.join(base, t.replace("\\", "/").replace("../runs/", "", 1)))
        # transcript field is relative to the runner cwd; rebuild from the run dir instead
        rel = t.replace("\\", "/")
        rel = rel.split("/cells/", 1)[-1]
        p = os.path.join(base, "cells", *rel.split("/"))
        cells[os.path.normpath(p)] = c

hit = 0
stats = collections.Counter()
per_cell = []
for p, c in cells.items():
    if not os.path.exists(p):
        stats["transcript missing"] += 1
        continue
    hit += 1
    counts = collections.defaultdict(int)   # (v1tool, path) -> n
    seq = []
    for line in open(p, encoding="utf-8", errors="replace"):
        m = LINE.search(line)
        if not m: continue
        verb, path = m.group(1), m.group(2).strip()
        v1tool, cap = V1[verb]
        counts[(v1tool, path)] += 1
        seq.append(v1tool)
    worst_w = max([n for (t, _), n in counts.items() if t == "file_write"], default=0)
    worst_e = max([n for (t, _), n in counts.items() if t == "file_edit"], default=0)
    # longest run of the same v1 tool name
    run = best = 0; prev = None
    for t in seq:
        run = run + 1 if t == prev else 1
        prev = t; best = max(best, run)
    per_cell.append(dict(status=c.get("status"), suite=c.get("suite"), task=c.get("task"),
                         muts=len(seq), w=worst_w, e=worst_e, longest_run=best,
                         trip_w=worst_w > 3, trip_e=worst_e > 5, trip_run=best >= 5))

print(f"cells matched to a transcript: {hit}/{len(cells)}  ({stats['transcript missing']} missing)")
def report(label, sel):
    sub = [r for r in per_cell if sel(r)]
    if not sub: return
    n = len(sub)
    tw = sum(r["trip_w"] for r in sub); te = sum(r["trip_e"] for r in sub)
    tr = sum(r["trip_run"] for r in sub)
    hard = sum(1 for r in sub if r["trip_w"] or r["trip_e"])
    any_ = sum(1 for r in sub if r["trip_w"] or r["trip_e"] or r["trip_run"])
    print(f"\n--- {label}  n={n} ---")
    print(f"  mutations/cell: max={max(r['muts'] for r in sub)} "
          f"mean={sum(r['muts'] for r in sub)/n:.1f} zero={sum(1 for r in sub if r['muts']==0)}")
    print(f"  file_write >3 on one path : {tw:4d}  = {100*tw/n:5.1f}%")
    print(f"  file_edit  >5 on one path : {te:4d}  = {100*te/n:5.1f}%")
    print(f"  per-path caps (either)    : {hard:4d}  = {100*hard/n:5.1f}%   <- faithful replay")
    print(f"  5-in-a-row same verb      : {tr:4d}  = {100*tr/n:5.1f}%   <- upper bound")
    print(f"  ANY v1 breaker fires      : {any_:4d}  = {100*any_/n:5.1f}%")

report("ALL cells with a transcript", lambda r: True)
report("cells that PASSED", lambda r: r["status"] == "pass")
report("K-suite (repository work)", lambda r: r["suite"] == "k")
report("K-suite that PASSED", lambda r: r["suite"] == "k" and r["status"] == "pass")

print("\nworst offenders (passing cells, by per-path count):")
for r in sorted([r for r in per_cell if r["status"]=="pass"], key=lambda r: -(max(r["w"], r["e"])))[:8]:
    print(f"  {r['suite']:>4} {r['task'][:38]:38} writes/path={r['w']} edits/path={r['e']} "
          f"muts={r['muts']} longest_run={r['longest_run']}")
