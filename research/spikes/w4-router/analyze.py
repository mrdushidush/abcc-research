"""W4 item 1 analysis: v1's complexity score against measured outcome, cost and
context occupancy, over 952 Q56 cells.  Everything stratified by arm.

Inputs: scores.jsonl (donor scorer), ctx.jsonl (recovered occupancy floor),
runs/q56/w8-*/cells.jsonl (outcomes).
"""
import json
import glob
import math
import os
import statistics as st
from collections import defaultdict

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
SPIKE = os.path.join(ROOT, "research", "spikes", "w4-router")


def jsonl(path, guard=True):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or (guard and not line.startswith("{")):
            continue
        yield json.loads(line)


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None

    def rank(v):
        order = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return None if dx == 0 or dy == 0 else num / (dx * dy)


scores = {r["id"]: r for r in jsonl(os.path.join(SPIKE, "scores.jsonl"))
          if r["suite"] == "q56"}
ctx = {}
for r in jsonl(os.path.join(SPIKE, "ctx.jsonl")):
    ctx[(r["run"], r["task"], r["variant"])] = r

cells = []
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "q56", "w8-*", "cells.jsonl"))):
    run = os.path.basename(os.path.dirname(f))
    for c in jsonl(f):
        c["_run"] = run
        cells.append(c)


def met(c, k):
    v = c.get("metrics", {}).get(k)
    return v["measured"] if isinstance(v, dict) and "measured" in v else None


# ---------------------------------------------------------------- occupancy
print("=== A. peak prompt occupancy (FLOOR), all 945 Q56 cells with a marker ===")
occ = [r for r in ctx.values() if r.get("peak_floor")]
vals = sorted(r["peak_floor"] for r in occ)
pre = st.median([r["preamble"] for r in occ])
print(f"  n={len(vals)}  min {vals[0]}  p50 {vals[len(vals)//2]}  "
      f"p90 {vals[int(len(vals)*0.9)]}  max {vals[-1]}")
print(f"  median preamble (system prompt + tool schemas) = {pre:.0f}"
      f"  -> {100*pre/vals[len(vals)//2]:.0f}% of the median peak")
for tier, lim in (("v1 8K (deprecated)", 8192), ("v1 16K default", 16384),
                  ("v1 32K top local", 32768), ("this run's num_ctx", 61440)):
    over = sum(1 for v in vals if v > lim)
    print(f"  cells whose FLOOR exceeds {tier:22s} ({lim:6d}): {over:4d} / {len(vals)}")
nomark = [r for r in ctx.values() if not r.get("peak_floor")]
print(f"  cells with NO turn-end marker: {len(nomark)} -> "
      f"{sorted(set((r['task'], r['variant']) for r in nomark))}")
print()

# ---------------------------------------------------------- cost vs occupancy
print("=== B. cumulative cost vs peak occupancy: the two are not one axis ===")
pairs = []
for c in cells:
    k = (c["_run"], c["task"], c["variant"])
    r = ctx.get(k)
    tin = met(c, "tokens_in")
    if r and r.get("peak_floor") and tin:
        pairs.append((r["peak_floor"], tin, c["variant"], c["task"], c["status"]))
occ_v = [p[0] for p in pairs]
tin_v = [p[1] for p in pairs]
print(f"  n={len(pairs)}  spearman(peak_floor, tokens_in_cumulative) = "
      f"{spearman(occ_v, tin_v):+.3f}")
print(f"  tokens_in cumulative: min {min(tin_v)}  p50 {sorted(tin_v)[len(tin_v)//2]}  "
      f"max {max(tin_v)}   ratio max/max-occupancy = {max(tin_v)/max(occ_v):.1f}x")
print()

# ------------------------------------------------- score vs everything, by arm
print("=== C. does v1's score predict outcome / cost / occupancy?  BY ARM ===")
for variant in ["control", "gated", "redirect-first-edit", "deny-first-edit"]:
    sel = [c for c in cells if c["variant"] == variant]
    agg = defaultdict(lambda: {"p": 0, "n": 0, "tin": [], "occ": [], "it": [], "w": []})
    for c in sel:
        a = agg[c["task"]]
        a["n"] += 1
        a["p"] += 1 if c["status"] == "pass" else 0
        t = met(c, "tokens_in")
        if t:
            a["tin"].append(t)
        r = ctx.get((c["_run"], c["task"], c["variant"]))
        if r and r.get("peak_floor"):
            a["occ"].append(r["peak_floor"])
        i = met(c, "iterations")
        if i is not None:
            a["it"].append(i)
        w = met(c, "wall_clock_s")
        if w:
            a["w"].append(w)
    tasks = [t for t in agg if t in scores]
    xs = [scores[t]["score"] for t in tasks]
    print(f"  -- {variant}  ({len(sel)} cells, {len(tasks)} tasks)")
    for label, f in (("pass rate", lambda a: a["p"] / a["n"]),
                     ("tokens_in", lambda a: st.mean(a["tin"]) if a["tin"] else 0),
                     ("peak_floor", lambda a: st.mean(a["occ"]) if a["occ"] else 0),
                     ("iterations", lambda a: st.mean(a["it"]) if a["it"] else 0),
                     ("wall_clock_s", lambda a: st.mean(a["w"]) if a["w"] else 0)):
        ys = [f(agg[t]) for t in tasks]
        rho = spearman(xs, ys)
        print(f"       spearman(score, {label:13s}) = "
              + (f"{rho:+.3f}" if rho is not None else "n/a"))
print()

# ------------------------------------------------ what DOES predict failure?
print("=== D. what does predict a control failure, if not the score? ===")
agg = defaultdict(lambda: {"p": 0, "n": 0, "occ": [], "tin": [], "it": []})
for c in cells:
    if c["variant"] != "control":
        continue
    a = agg[c["task"]]
    a["n"] += 1
    a["p"] += 1 if c["status"] == "pass" else 0
    r = ctx.get((c["_run"], c["task"], c["variant"]))
    if r and r.get("peak_floor"):
        a["occ"].append(r["peak_floor"])
    t = met(c, "tokens_in")
    if t:
        a["tin"].append(t)
    i = met(c, "iterations")
    if i is not None:
        a["it"].append(i)
tasks = sorted(agg)
fail = [1 - agg[t]["p"] / agg[t]["n"] for t in tasks]
for label, ys in (
    ("v1 score", [scores[t]["score"] for t in tasks]),
    ("prompt words", [scores[t]["words"] for t in tasks]),
    ("peak_floor", [st.mean(agg[t]["occ"]) if agg[t]["occ"] else 0 for t in tasks]),
    ("tokens_in", [st.mean(agg[t]["tin"]) if agg[t]["tin"] else 0 for t in tasks]),
    ("iterations", [st.mean(agg[t]["it"]) if agg[t]["it"] else 0 for t in tasks]),
):
    rho = spearman(ys, fail)
    print(f"  spearman({label:14s}, control failure rate) = "
          + (f"{rho:+.3f}" if rho is not None else "n/a"))
print()
print("  by donor 'kind' (control arm):")
byk = defaultdict(lambda: [0, 0])
for t in tasks:
    k = scores[t]["kind"]
    byk[k][0] += agg[t]["p"]
    byk[k][1] += agg[t]["n"]
for k, (p, n) in sorted(byk.items(), key=lambda kv: kv[1][0] / kv[1][1]):
    print(f"    {k:16s} {100*p/n:5.1f}%  ({p:3d}/{n:3d})   "
          f"mean v1 score {st.mean([scores[t]['score'] for t in tasks if scores[t]['kind']==k]):.2f}")
print()
print("  by language (control arm):")
byl = defaultdict(lambda: [0, 0])
for t in tasks:
    lang = scores[t]["lang"]
    byl[lang][0] += agg[t]["p"]
    byl[lang][1] += agg[t]["n"]
for k, (p, n) in sorted(byl.items(), key=lambda kv: kv[1][0] / kv[1][1]):
    print(f"    {k:12s} {100*p/n:5.1f}%  ({p:3d}/{n:3d})   "
          f"mean v1 score {st.mean([scores[t]['score'] for t in tasks if scores[t]['lang']==k]):.2f}")
