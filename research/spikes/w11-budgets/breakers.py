"""W11 item 5 — do the two breaker units measure the same thing, and does either
one predict failure? Answers four questions against the measured cells:

  1. overlap: does an iteration cap and a wall-clock deadline cut the same cells?
  2. dispersion: how much does seconds-per-iteration vary (i.e. is a time budget
     a proxy for a work budget)?
  3. discrimination: is a long attempt a *stuck* attempt, or a hard one?
  3b. the same, stratified by variant — Q56's deny/redirect/gated arms exist to
     INTERRUPT the agent, so pooling them with the controls invents a
     low-iteration failure shoulder that is not there.
"""
import json, glob, os, statistics, collections

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
rows = []
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "**", "cells.jsonl"), recursive=True)):
    run = os.path.relpath(f, os.path.join(ROOT, "runs"))
    for line in open(f, encoding="utf-8"):
        if not line.strip():
            continue
        c = json.loads(line)
        m = c.get("metrics", {})
        g = lambda k: (m.get(k) or {}).get("measured") if isinstance(m.get(k), dict) else None
        rows.append(dict(run=run, suite=c.get("suite"), task=c.get("task"),
                         status=c.get("status"), variant=c.get("variant"),
                         iters=g("iterations"), wall=g("wall_clock_s"),
                         tout=g("tokens_out"), tin=g("tokens_in")))

full = [r for r in rows if r["iters"] and r["wall"]]
print(f"cells with both iterations and wall clock: {len(full)}")

# 1. overlap
ITER_CAP, TIME_CAP = 25, 300
a = {id(r) for r in full if r["iters"] > ITER_CAP}
b = {id(r) for r in full if r["wall"] > TIME_CAP}
print(f"\n1. OVERLAP at iter>{ITER_CAP} and wall>{TIME_CAP}s")
print(f"   iteration cap alone cuts : {len(a)}")
print(f"   time deadline alone cuts : {len(b)}")
print(f"   both                     : {len(a & b)}")
print(f"   union                    : {len(a | b)}")
print(f"   Jaccard                  : {len(a & b)/max(1, len(a | b)):.2f}")

# 2. dispersion of seconds per iteration
spi = sorted(r["wall"]/r["iters"] for r in full)
q = lambda p: spi[int((len(spi)-1)*p/100)]
print(f"\n2. SECONDS PER ITERATION  n={len(spi)}")
print(f"   min={spi[0]:.2f} p10={q(10):.2f} p50={q(50):.2f} p90={q(90):.2f} "
      f"p99={q(99):.2f} max={spi[-1]:.2f}")
for lbl, sel in (("champion K", lambda r: r["suite"] == "k" and "champ" in r["run"]),
                 ("27B K",      lambda r: r["suite"] == "k" and "27b" in r["run"]),
                 ("q56/u100",   lambda r: r["suite"] != "k")):
    s = sorted(r["wall"]/r["iters"] for r in full if sel(r))
    if s:
        print(f"   {lbl:>10}: n={len(s):4d} median={statistics.median(s):6.2f} max={s[-1]:7.2f} s/iter")

# 3. discrimination
graded = [r for r in full if r["status"] in ("pass", "fail")]
print(f"\n3. DISCRIMINATION  (pass|fail cells only, n={len(graded)})")

def buckets(pop, key, edges, unit, indent="   "):
    for lo, hi in zip([0]+edges, edges+[float('inf')]):
        sub = [r for r in pop if lo <= r[key] < hi]
        if not sub:
            continue
        p = sum(1 for r in sub if r["status"] == "pass")
        hi_s = "inf" if hi == float('inf') else f"{hi:g}"
        print(f"{indent}[{lo:>5g},{hi_s:>5}) {unit}: n={len(sub):4d} pass={p:4d} "
              f"rate={100*p/len(sub):5.1f}%")

print("   by wall:")
buckets(graded, "wall", [30, 60, 120, 300, 600], "s", "     ")
print("   by iters:")
buckets(graded, "iters", [6, 10, 15, 20, 25, 30], "it", "     ")

# 3b. stratified by variant
print("\n3b. STRATIFIED BY VARIANT (the pooled low shoulder is an artifact)")
print("   variants:", dict(collections.Counter(r["variant"] for r in graded)))
for label, sel in (("control", lambda r: r["variant"] == "control"),
                   ("interfered-with", lambda r: r["variant"] != "control")):
    sub = [r for r in graded if sel(r)]
    print(f"   --- {label}  n={len(sub)} ---")
    buckets(sub, "iters", [6, 10, 15, 20, 25, 30], "it", "     ")
    buckets(sub, "wall", [30, 60, 120, 300], "s", "     ")
