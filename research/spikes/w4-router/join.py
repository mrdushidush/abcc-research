"""Join v1's complexity score to the measured outcome of every Q56 cell.

Scores come from score_corpus.mjs (the DONOR'S OWN compiled calculateComplexity).
Outcomes come from runs/q56/w8-*/cells.jsonl -- 8 runs, one subject, one held
config (champion, num_ctx 61440, max_iterations 40).  runs/q56-degraded is
EXCLUDED: different config.

Everything is stratified by variant.  448 of the Q56 cells come from arms built
to stop the agent editing; a pooled rate over them is a claim about the arm.
"""
import json
import glob
import math
import os
import statistics as st
from collections import defaultdict

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"


def load_scores():
    out = {}
    p = os.path.join(ROOT, "research", "spikes", "w4-router", "scores.jsonl")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        r = json.loads(line)
        out[(r["suite"], r["id"])] = r
    return out


def load_cells():
    cells = []
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", "q56", "w8-*", "cells.jsonl"))):
        run = os.path.basename(os.path.dirname(f))
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            c["_run"] = run
            cells.append(c)
    return cells


def m(cell, key):
    v = cell.get("metrics", {}).get(key)
    if isinstance(v, dict) and "measured" in v:
        return v["measured"]
    return None


def spearman(xs, ys):
    """Spearman rho with average ranks; returns None if degenerate."""
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
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def main():
    scores = load_scores()
    cells = load_cells()
    print(f"cells loaded: {len(cells)}  from runs: "
          f"{sorted(set(c['_run'] for c in cells))}")
    print(f"variants: {sorted(set(c['variant'] for c in cells))}")
    print()

    # --- 1. What tier does v1 assign, over the whole corpus? -----------------
    print("=== 1. v1 tier assignment over 149 corpus tasks (its own scorer) ===")
    tiers = defaultdict(list)
    for (suite, tid), r in scores.items():
        s = r["score"]
        if s >= 10:
            t = "C10 decomposition -> Sonnet"
        elif s >= 9:
            t = "C9 extreme -> 32K"
        elif s >= 7:
            t = "C7-C8 complex -> 32K / remote"
        else:
            t = "C1-C6 -> local 16K"
        tiers[t].append((suite, tid, s))
    for t in sorted(tiers):
        print(f"  {t:32s} {len(tiers[t]):4d}")
    alls = [r["score"] for r in scores.values()]
    print(f"  min {min(alls)}  max {max(alls)}  median {st.median(alls)}")
    print()

    # --- 2. pass rate by score bucket, PER ARM -------------------------------
    by_arm_score = defaultdict(lambda: [0, 0])   # (variant, score) -> [pass, n]
    per_task = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # task->variant->[pass,n]
    for c in cells:
        key = ("q56", c["task"])
        if key not in scores:
            continue
        s = scores[key]["score"]
        v = c["variant"]
        ok = 1 if c["status"] == "pass" else 0
        by_arm_score[(v, s)][0] += ok
        by_arm_score[(v, s)][1] += 1
        per_task[c["task"]][v][0] += ok
        per_task[c["task"]][v][1] += 1

    print("=== 2. Q56 pass rate by v1 complexity score, STRATIFIED BY ARM ===")
    variants = sorted(set(v for (v, _) in by_arm_score))
    svals = sorted(set(s for (_, s) in by_arm_score))
    hdr = "  score | " + " | ".join(f"{v:>20s}" for v in variants)
    print(hdr)
    for s in svals:
        row = f"  {s:5.1f} | "
        cellsr = []
        for v in variants:
            p, n = by_arm_score.get((v, s), [0, 0])
            cellsr.append(f"{(100*p/n if n else 0):5.1f}% ({p:3d}/{n:3d})" if n else " " * 20)
        print(row + " | ".join(f"{c:>20s}" for c in cellsr))
    print()

    # --- 3. correlations, control arm only -----------------------------------
    print("=== 3. Does the score predict anything? (control arm, per task) ===")
    xs, ys_pass, ys_iter, ys_tin, ys_wall = [], [], [], [], []
    ctrl_cells = [c for c in cells if c["variant"] == "control"]
    agg = defaultdict(lambda: {"pass": 0, "n": 0, "iter": [], "tin": [], "wall": []})
    for c in ctrl_cells:
        t = c["task"]
        a = agg[t]
        a["n"] += 1
        a["pass"] += 1 if c["status"] == "pass" else 0
        for k, key in (("iter", "iterations"), ("tin", "tokens_in"), ("wall", "wall_clock_s")):
            v = m(c, key)
            if v is not None:
                a[k].append(v)
    for t, a in sorted(agg.items()):
        key = ("q56", t)
        if key not in scores:
            continue
        xs.append(scores[key]["score"])
        ys_pass.append(a["pass"] / a["n"])
        ys_iter.append(st.mean(a["iter"]) if a["iter"] else 0)
        ys_tin.append(st.mean(a["tin"]) if a["tin"] else 0)
        ys_wall.append(st.mean(a["wall"]) if a["wall"] else 0)
    print(f"  n tasks = {len(xs)}, control cells = {len(ctrl_cells)}")
    for name, ys in (("pass rate", ys_pass), ("iterations", ys_iter),
                     ("tokens_in", ys_tin), ("wall_clock_s", ys_wall)):
        rho = spearman(xs, ys)
        print(f"  spearman(score, {name:14s}) = "
              + (f"{rho:+.3f}" if rho is not None else "n/a"))
    print()

    # --- 4. the hardest tasks vs the score -----------------------------------
    print("=== 4. hardest and easiest control tasks vs v1's score ===")
    ranked = sorted(agg.items(), key=lambda kv: kv[1]["pass"] / kv[1]["n"])
    print("  HARDEST (lowest control pass rate):")
    for t, a in ranked[:8]:
        s = scores[("q56", t)]
        print(f"    {t}  pass {a['pass']}/{a['n']}  score {s['score']:.1f}  "
              f"lang {s['lang']:10s} kind {s['kind']}")
    print("  EASIEST:")
    for t, a in ranked[-6:]:
        s = scores[("q56", t)]
        print(f"    {t}  pass {a['pass']}/{a['n']}  score {s['score']:.1f}  "
              f"lang {s['lang']:10s} kind {s['kind']}")
    print()

    # --- 5. context: does score predict tokens? ------------------------------
    print("=== 5. difficulty vs context: measured tokens_in on control ===")
    tins = [y for y in ys_tin if y]
    print(f"  tokens_in: min {min(tins):.0f}  median {st.median(tins):.0f}  "
          f"max {max(tins):.0f}")
    over16k = sum(1 for y in ys_tin if y > 16384)
    over32k = sum(1 for y in ys_tin if y > 32768)
    print(f"  tasks whose MEAN control tokens_in exceeds v1's 16K tier: {over16k}/{len(ys_tin)}")
    print(f"  ... exceeds v1's 32K tier:                                {over32k}/{len(ys_tin)}")
    percell = [m(c, "tokens_in") for c in ctrl_cells if m(c, "tokens_in")]
    print(f"  per-cell control tokens_in > 16384: "
          f"{sum(1 for v in percell if v > 16384)}/{len(percell)}")
    print(f"  per-cell control tokens_in > 32768: "
          f"{sum(1 for v in percell if v > 32768)}/{len(percell)}")
    allcell = [m(c, "tokens_in") for c in cells if m(c, "tokens_in")]
    print(f"  per-cell ALL-ARM tokens_in > 16384: "
          f"{sum(1 for v in allcell if v > 16384)}/{len(allcell)}  "
          f"max {max(allcell)}")


if __name__ == "__main__":
    main()
