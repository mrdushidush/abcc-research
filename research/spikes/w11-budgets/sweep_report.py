"""W11 item 5 — read out the loop-budget sweep.

`run_budget_sweep.sh` runs the K suite on the champion at CLAUDETTE_MAX_ITERATIONS
in {12, 20, 40}, three reps each, one variable. This prints the pass rate per
budget, per task, and how often the cap was actually reached — because a budget
only explains an outcome on the cells that hit it.

k-champ-r{1,2,3} (the W1 baseline, same subject and corpus, budget 40) is printed
alongside as an external replication of the 40 arm.
"""
import json, glob, os, collections

ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")

def load(pattern):
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "runs", pattern, "**", "cells.jsonl"), recursive=True)):
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            c = json.loads(line)
            m = c.get("metrics", {})
            g = lambda k: (m.get(k) or {}).get("measured") if isinstance(m.get(k), dict) else None
            out.append(dict(task=c["task"], status=c["status"], it=g("iterations"),
                            wall=g("wall_clock_s"), tout=g("tokens_out"),
                            run=os.path.relpath(f, os.path.join(ROOT, "runs"))))
    return out

arms = {b: load(f"w11-b{b}-r*") for b in (12, 20, 40)}
arms["40 (W1 baseline, k-champ)"] = load("k-champ-r*")

print(f"{'budget':<26} {'n':>3} {'pass':>5} {'rate':>7} {'at cap':>7} {'med it':>7} {'med s':>8}")
for label, cells in arms.items():
    if not cells:
        continue
    n = len(cells)
    p = sum(1 for c in cells if c["status"] == "pass")
    its = sorted(c["it"] for c in cells if c["it"])
    walls = sorted(c["wall"] for c in cells if c["wall"])
    cap = None
    try:
        cap = int(str(label).split()[0])
    except ValueError:
        pass
    atcap = sum(1 for c in cells if c["it"] and cap and c["it"] >= cap) if cap else 0
    med = lambda xs: xs[len(xs)//2] if xs else float('nan')
    print(f"{str(label):<26} {n:>3} {p:>5} {100*p/n:>6.1f}% {atcap:>7} {med(its):>7} {med(walls):>8.1f}")

print("\nper task:")
tasks = sorted({c["task"] for cells in arms.values() for c in cells})
hdr = "  " + f"{'task':<34}" + "".join(f"{str(k):>28}" for k in arms)
print(hdr)
for t in tasks:
    row = f"  {t:<34}"
    for label, cells in arms.items():
        sub = [c for c in cells if c["task"] == t]
        if not sub:
            row += f"{'-':>28}"
            continue
        marks = "".join("P" if c["status"] == "pass" else ("T" if c["status"] == "timeout" else "f")
                        for c in sub)
        its = ",".join(str(c["it"]) if c["it"] else "-" for c in sub)
        row += f"{marks + ' it=' + its:>28}"
    print(row)

print("\ncells that reached their cap (a truncated attempt), by budget:")
for label, cells in arms.items():
    try:
        cap = int(str(label).split()[0])
    except ValueError:
        continue
    hit = [c for c in cells if c["it"] and c["it"] >= cap]
    for c in hit:
        print(f"  budget {cap:>2}  {c['task'][:34]:34} {c['status']:5} it={c['it']} wall={c['wall']:.1f}")

# The graceful landing: when the cap is reached Claudette makes one extra
# text-only call. If that call returns no usable text it substitutes an honest
# fallback line instead ("produced no summary", conversation.rs:914-939). Count
# how often the landing actually produced a state-of-work note on this model.
print("\ngraceful landing outcomes (cells that reached the cap):")
tot = good = 0
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "w11-b*", "**", "transcript.log"), recursive=True)):
    if os.sep + "warmup" + os.sep in f:
        continue
    body = open(f, encoding="utf-8", errors="replace").read()
    if "hit the iteration cap" not in body:
        continue
    tot += 1
    if "produced no summary" not in body:
        good += 1
if tot:
    print(f"  landings: {tot}   produced a real summary: {good}   "
          f"fell back to the honest line: {tot-good}  ({100*(tot-good)/tot:.0f}%)")
else:
    print("  no cell reached its cap")
