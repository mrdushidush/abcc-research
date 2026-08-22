"""W11 item 5 — census of attempt cost across every measured cell in this repo.

Reads every runs/**/cells.jsonl and reports the distribution of wall-clock and
iteration count, so v1's loop budgets can be placed as percentiles on real data
from this hardware rather than compared to their own comments.
"""
import json, glob, os, statistics, sys, collections

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
files = sorted(glob.glob(os.path.join(ROOT, "runs", "**", "cells.jsonl"), recursive=True))

rows = []
for f in files:
    run = os.path.relpath(f, os.path.join(ROOT, "runs"))
    with open(f, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            m = c.get("metrics", {})
            def val(k):
                v = m.get(k)
                if isinstance(v, dict) and "measured" in v:
                    return v["measured"]
                return None
            rows.append({
                "run": run,
                "suite": c.get("suite"),
                "task": c.get("task"),
                "variant": c.get("variant"),
                "status": c.get("status"),
                "iters": val("iterations"),
                "wall": val("wall_clock_s"),
                "tin": val("tokens_in"),
                "tout": val("tokens_out"),
            })

print(f"files={len(files)} cells={len(rows)}")
by_suite = collections.Counter(r["suite"] for r in rows)
print("suites:", dict(by_suite))
print("statuses:", dict(collections.Counter(r["status"] for r in rows)))

def pct(xs, p):
    xs = sorted(xs)
    if not xs: return None
    k = (len(xs) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)

def report(label, sel):
    sub = [r for r in rows if sel(r)]
    walls = [r["wall"] for r in sub if r["wall"] is not None]
    iters = [r["iters"] for r in sub if r["iters"] is not None]
    if not sub: return
    print(f"\n--- {label}  n={len(sub)} (wall n={len(walls)}, iters n={len(iters)}) ---")
    if walls:
        print(f"  wall_clock_s: min={min(walls):.1f} p50={pct(walls,50):.1f} p90={pct(walls,90):.1f} "
              f"p95={pct(walls,95):.1f} max={max(walls):.1f} mean={statistics.mean(walls):.1f}")
        for thr, name in ((300, "v1 stuck deadline 300s"), (600, "v1 EXECUTE_TIMEOUT 600s"),
                          (900, "15 min"), (1800, "v1 MISSION_TIMEOUT 1800s")):
            n = sum(1 for w in walls if w > thr)
            print(f"    > {thr:5d}s ({name}): {n}/{len(walls)} = {100*n/len(walls):.1f}%")
    if iters:
        print(f"  iterations:   min={min(iters)} p50={pct(iters,50):.0f} p90={pct(iters,90):.0f} "
              f"p95={pct(iters,95):.0f} max={max(iters)} mean={statistics.mean(iters):.1f}")
        for thr, name in ((20, "v1 CTO max_iter"), (25, "v1 Coder max_iter"),
                          (50, "v1 QA max_iter / MAX_TOTAL_TOOL_CALLS")):
            n = sum(1 for i in iters if i > thr)
            print(f"    > {thr:3d} ({name}): {n}/{len(iters)} = {100*n/len(iters):.1f}%")
        cap = sum(1 for i in iters if i >= 40)
        print(f"    at/over harness cap 40: {cap}/{len(iters)} = {100*cap/len(iters):.1f}%  (censoring)")

report("ALL cells", lambda r: True)
report("K-suite (repository work, champion)", lambda r: r["suite"] == "k" and "champ" in r["run"])
report("K-suite (repository work, 27B)", lambda r: r["suite"] == "k" and "27b" in r["run"])
report("Q56 / W8 corpus", lambda r: r["suite"] != "k")

# passing cells only — the honest denominator for "would the cap have killed useful work"
report("ALL cells that PASSED", lambda r: r["status"] == "pass")
