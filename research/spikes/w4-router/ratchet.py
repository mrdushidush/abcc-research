"""F221's ratchet, made concrete on the 149 real prompts.

v1 calls the model half whenever `routerComplexity <= 8` (taskRouter.ts:297) and
then blends (complexityAssessor.ts:137-154):
    diff = model - rules
    diff >=  2  ->  final = model                      (model taken OUTRIGHT)
    diff <= -2  ->  final = 0.6*rules + 0.4*model      (damped toward rules)
    otherwise   ->  final = (rules + model) / 2        (average)

With the rules pinned low on every real task, the question is what share of the
model's 1..10 answers land in each branch, and how much of the final score is
the model's.
"""
import json
import os
import statistics as st
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, "scores.jsonl"), encoding="utf-8")
        if l.strip().startswith("{")]

print(f"tasks: {len(rows)}")
print(f"rules score: min {min(r['score'] for r in rows)}  "
      f"p50 {st.median([r['score'] for r in rows])}  "
      f"max {max(r['score'] for r in rows)}")
gate = sum(1 for r in rows if r["score"] <= 8)
print(f"tasks where the model half is CALLED (rules <= 8): {gate}/{len(rows)}")
print()

branch = Counter()
outright = Counter()
for r in rows:
    rules = r["score"]
    for model in range(1, 11):
        d = model - rules
        if d >= 2:
            branch["model taken outright"] += 1
            outright[model] += 1
        elif d <= -2:
            branch["damped toward rules"] += 1
        else:
            branch["averaged"] += 1
tot = sum(branch.values())
print("over the 149 x 10 (task, model answer) grid:")
for k, v in branch.most_common():
    print(f"  {k:22s} {v:5d}  {100*v/tot:5.1f}%")
print()

# The model answer at which the model wins outright, per task.
th = [min(m for m in range(1, 11) if m - r["score"] >= 2) for r in rows]
print(f"model answer at which it is taken OUTRIGHT: min {min(th)}  "
      f"p50 {st.median(th)}  max {max(th)}")
print(f"  tasks where a model answer of 4 already wins outright: "
      f"{sum(1 for t in th if t <= 4)}/{len(rows)}")
print(f"  tasks where a model answer of 6 already wins outright: "
      f"{sum(1 for t in th if t <= 6)}/{len(rows)}")
print()

# Can the pair ever reach v1's tiers?
print("what final score is REACHABLE, per task, over model answers 1..10:")
reach7 = reach9 = reach10 = 0
for r in rows:
    rules = r["score"]
    finals = []
    for model in range(1, 11):
        d = model - rules
        if d >= 2:
            f = model
        elif d <= -2:
            f = rules * 0.6 + model * 0.4
        else:
            f = (rules + model) / 2
        finals.append(round(f * 10) / 10)
    if max(finals) >= 7:
        reach7 += 1
    if max(finals) >= 9:
        reach9 += 1
    if max(finals) >= 10:
        reach10 += 1
print(f"  can reach >= 7 (32K / remote tier): {reach7}/{len(rows)}")
print(f"  can reach >= 9 (extreme):           {reach9}/{len(rows)}")
print(f"  can reach 10 (Sonnet):              {reach10}/{len(rows)}")
print()
print("floor: what the rules alone guarantee (model answer 1, worst case):")
floors = []
for r in rows:
    rules = r["score"]
    d = 1 - rules
    f = rules if d >= 2 else (rules * 0.6 + 1 * 0.4 if d <= -2 else (rules + 1) / 2)
    floors.append(round(f * 10) / 10)
print(f"  min {min(floors)}  p50 {st.median(floors)}  max {max(floors)}")
