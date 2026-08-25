"""W4 item 3, step 1: the population an estimator can be scored against.

One row per task that has BOTH a prompt (the thing an estimator sees before
dispatch) and a measured outcome (the answer key).  Carries every FREE a-priori
feature item 1 already priced, so the model arms are compared against the same
baselines on the same rows:

    v1 rule score   rho = +0.101   (F362)
    prompt words    rho = +0.187   (F362)
    BCF rule_score  rho = +0.219   (F362)  <- the bar

Outcome is the CONTROL arm only.  672 of the 952 Q56 cells are non-control and
560 come from arms built to stop the agent editing; pooling them measures the
arm (memory items 26/28/31).  K is stratified to the champion at
max_iterations = 40 -- the six k-27b families are a different model and
w11-b12/b20 are different loop budgets (spike trap 9).
"""
import json
import glob
import os
import tomllib
from collections import defaultdict

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
HERE = os.path.dirname(os.path.abspath(__file__))
W4R = os.path.join(ROOT, "research", "spikes", "w4-router")

POPS = {
    "q56": ["runs/q56/w8-*"],
    "u100": ["runs/w8-*", "runs/prefix-invalid/w8-*"],
    "k": ["runs/k-champ-r*/w8-*", "runs/w11-b40-r*/w8-*"],
}


def jsonl(p):
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line.startswith("{"):
            yield json.loads(line)


v1 = {(r["suite"], r["id"]): r["score"] for r in jsonl(os.path.join(W4R, "scores.jsonl"))}
bcf = {(r["suite"], r["id"]): r["bcf_score"]
       for r in jsonl(os.path.join(W4R, "bcf_scores.jsonl"))}

# ---- outcomes, control arm only ----------------------------------------------
out = defaultdict(lambda: {"n": 0, "pass": 0, "variants": set()})
for suite, pats in POPS.items():
    for pat in pats:
        for run_dir in sorted(glob.glob(os.path.join(ROOT, pat))):
            cp = os.path.join(run_dir, "cells.jsonl")
            if not os.path.isfile(cp):
                continue
            for c in jsonl(cp):
                if c["variant"] != "control":
                    continue
                a = out[(suite, c["task"])]
                a["n"] += 1
                a["pass"] += 1 if c["status"] == "pass" else 0
                a["variants"].add(os.path.basename(run_dir))

# ---- fixture profile ---------------------------------------------------------
def fixture_profile(suite, tid):
    d = os.path.join(ROOT, "corpus", "suites", suite, "tasks", tid, "fixture")
    nb, nf = 0, 0
    for root, _, files in os.walk(d):
        for f in files:
            if f == ".gitkeep":
                continue
            nb += os.path.getsize(os.path.join(root, f))
            nf += 1
    return nb, nf


rows = []
for suite in POPS:
    tdir = os.path.join(ROOT, "corpus", "suites", suite, "tasks")
    for tid in sorted(os.listdir(tdir)):
        key = (suite, tid)
        if key not in out:
            continue
        meta = tomllib.load(open(os.path.join(tdir, tid, "task.toml"), "rb"))
        prompt = open(os.path.join(tdir, tid, "prompt.txt"), encoding="utf-8").read()
        nb, nf = fixture_profile(suite, tid)
        a = out[key]
        rows.append({
            "suite": suite,
            "id": tid,
            "title": meta.get("title", ""),
            "lang": meta.get("lang", ""),
            "kind": meta.get("kind", ""),
            "prompt": prompt,
            "prompt_words": len(prompt.split()),
            "prompt_bytes": len(prompt.encode("utf-8")),
            "fixture_bytes": nb,
            "fixture_files": nf,
            "v1_score": v1.get(key),
            "bcf_score": bcf.get(key),
            "control_n": a["n"],
            "control_pass": a["pass"],
            "control_rate": a["pass"] / a["n"],
            "runs": sorted(a["variants"]),
        })

with open(os.path.join(HERE, "tasks.jsonl"), "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")

print(f"=== population: {len(rows)} tasks with a prompt and a control-arm answer key ===")
for suite in POPS:
    s = [r for r in rows if r["suite"] == suite]
    cells = sum(r["control_n"] for r in s)
    reps = sorted(set(r["control_n"] for r in s))
    print(f"  {suite:5s}  {len(s):3d} tasks  {cells:4d} control cells  repeats {reps}")
print()
print("=== outcome distribution (the thing an estimator has to predict) ===")
for suite in POPS:
    s = [r for r in rows if r["suite"] == suite]
    dist = defaultdict(int)
    for r in s:
        dist[round(r["control_rate"], 3)] += 1
    print(f"  {suite:5s}  " + "  ".join(f"{k:.2f}:{v}" for k, v in sorted(dist.items())))
print()
print("=== never passes / always passes ===")
for suite in POPS:
    s = [r for r in rows if r["suite"] == suite]
    zero = [r["id"] for r in s if r["control_pass"] == 0]
    full = [r["id"] for r in s if r["control_pass"] == r["control_n"]]
    print(f"  {suite:5s}  0/n: {zero}")
    print(f"         n/n: {len(full)} of {len(s)}")
print()
print("=== kind x control rate (the free a-priori feature nobody scored, OQ-W4-5) ===")
for suite in POPS:
    agg = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        if r["suite"] != suite:
            continue
        a = agg[r["kind"]]
        a[0] += r["control_pass"]
        a[1] += r["control_n"]
        a[2] += 1
    print(f"  -- {suite}")
    for k, (p, n, t) in sorted(agg.items(), key=lambda kv: kv[1][0] / kv[1][1]):
        print(f"     {k:16s} {100*p/n:5.1f}%  ({p:3d}/{n:3d})  {t} tasks")
