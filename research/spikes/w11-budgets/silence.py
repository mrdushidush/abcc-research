"""W11 item 5 — how long is a working agent silent, seen from outside?

An idle-gap ("no progress") timeout needs a number. This measures the two
signals a supervisor could actually clock, across every transcript in runs/:

  A. gap between consecutive transcript lines  — what a pipe-watching supervisor sees
  B. gap between consecutive MUTATIONS (▸ ...) — what a workspace-watching supervisor sees

Both are computed on cells that PASSED, because the floor for any timeout is
"the longest silence a successful attempt produced".
"""
import json, glob, os, re, statistics

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
TS = re.compile(r"^\[\s*(\d+)ms\]")
MUT = re.compile(r"▸ (write_file|apply_diff|edit_file|apply_patch):")

cells = {}
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "**", "cells.jsonl"), recursive=True)):
    base = os.path.dirname(f)
    for line in open(f, encoding="utf-8"):
        if not line.strip(): continue
        c = json.loads(line)
        t = (c.get("transcript") or "").replace("\\", "/")
        if "/cells/" not in t: continue
        p = os.path.normpath(os.path.join(base, "cells", *t.split("/cells/", 1)[1].split("/")))
        cells[p] = c

def gaps(path):
    line_ts, mut_ts = [], []
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            m = TS.match(line)
            if not m: continue
            ms = int(m.group(1))
            line_ts.append(ms)
            if MUT.search(line): mut_ts.append(ms)
    except OSError:
        return None, None
    dl = [b - a for a, b in zip(line_ts, line_ts[1:])]
    dm = [b - a for a, b in zip(mut_ts, mut_ts[1:])]
    return dl, dm

rows = []
for p, c in cells.items():
    if not os.path.exists(p): continue
    dl, dm = gaps(p)
    if dl is None: continue
    rows.append(dict(status=c.get("status"), suite=c.get("suite"), task=c.get("task"),
                     run=p, max_line_gap=max(dl, default=0), max_mut_gap=max(dm, default=0),
                     n_line=len(dl)+1, n_mut=len(dm)+1))

def q(xs, p):
    xs = sorted(xs); k = (len(xs)-1)*p/100
    lo, hi = int(k), min(int(k)+1, len(xs)-1)
    return xs[lo] + (xs[hi]-xs[lo])*(k-lo)

def report(label, sel, key):
    sub = [r for r in rows if sel(r) and r[key] > 0]
    if not sub: return
    v = [r[key]/1000 for r in sub]
    print(f"  {label:28} n={len(sub):4d}  p50={q(v,50):6.1f}s p90={q(v,90):7.1f}s "
          f"p99={q(v,99):7.1f}s max={max(v):7.1f}s")

print(f"transcripts parsed: {len(rows)}\n")
print("A. longest gap between consecutive TRANSCRIPT LINES (stdout/stderr watcher):")
report("all cells", lambda r: True, "max_line_gap")
report("passing cells", lambda r: r["status"] == "pass", "max_line_gap")
report("passing, K suite", lambda r: r["status"]=="pass" and r["suite"]=="k", "max_line_gap")
print("\nB. longest gap between consecutive MUTATIONS (workspace watcher):")
report("all cells", lambda r: True, "max_mut_gap")
report("passing cells", lambda r: r["status"] == "pass", "max_mut_gap")
report("passing, K suite", lambda r: r["status"]=="pass" and r["suite"]=="k", "max_mut_gap")

print("\nlongest silences on cells that PASSED (line gap):")
for r in sorted([r for r in rows if r["status"]=="pass"], key=lambda r: -r["max_line_gap"])[:8]:
    print(f"  {r['suite']:>4} {r['task'][:32]:32} silence={r['max_line_gap']/1000:7.1f}s "
          f"lines={r['n_line']:3d} muts={r['n_mut']}")

# what a 60s / 120s / 300s idle timeout would have killed
print("\nfalse kills by an idle-gap timeout on the LINE signal, passing cells only:")
p = [r for r in rows if r["status"] == "pass"]
for thr in (30, 60, 120, 300, 600):
    n = sum(1 for r in p if r["max_line_gap"] > thr*1000)
    print(f"  idle-gap {thr:4d}s: kills {n:4d}/{len(p)} = {100*n/len(p):5.1f}% of successful attempts")
