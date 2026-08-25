"""Follow-ups: which tasks reach BCF's Complex tier without the html floor,
does BCF's score predict Q56 outcome, and are the web tasks it floors to C7
actually harder?
"""
import json
import glob
import math
import os
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"


def jsonl(p):
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line.startswith("{"):
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


bcf = {(r["suite"], r["id"]): r for r in jsonl(os.path.join(HERE, "bcf_scores.jsonl"))}
v1 = {(r["suite"], r["id"]): r for r in jsonl(os.path.join(HERE, "scores.jsonl"))}

CORPUS = os.path.join(ROOT, "corpus", "suites")


def prompt_of(suite, tid):
    p = os.path.join(CORPUS, suite, "tasks", tid, "prompt.txt")
    return open(p, encoding="utf-8").read().lower() if os.path.isfile(p) else ""


print("=== tasks reaching BCF's C7 WITHOUT the html/landing-page/website floor ===")
for k, r in sorted(bcf.items()):
    if r["bcf_score"] < 7:
        continue
    t = prompt_of(*k)
    web = any(w in t for w in ("html", "landing page", "website"))
    if not web:
        print(f"  {k[0]}/{k[1]}  BCF {r['bcf_score']}  (not web-floored)  "
              f"v1 {v1[k]['score']}")
print()

# ---- Q56 outcomes ----
cells = []
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "q56", "w8-*", "cells.jsonl"))):
    for c in jsonl(f):
        cells.append(c)
agg = defaultdict(lambda: [0, 0])
for c in cells:
    if c["variant"] != "control":
        continue
    a = agg[c["task"]]
    a[1] += 1
    a[0] += 1 if c["status"] == "pass" else 0
tasks = sorted(agg)
fail = [1 - agg[t][0] / agg[t][1] for t in tasks]
print("=== does EITHER donor scorer predict Q56 control failure? ===")
for name, xs in (("v1 rule score", [v1[("q56", t)]["score"] for t in tasks]),
                 ("BCF rule_score", [bcf[("q56", t)]["bcf_score"] for t in tasks])):
    print(f"  spearman({name:15s}, failure rate) = {spearman(xs, fail):+.3f}")
print()

# ---- u100 outcomes: are the web tasks harder? ----
u = []
for f in sorted(glob.glob(os.path.join(ROOT, "runs", "w8-*", "cells.jsonl"))):
    for c in jsonl(f):
        u.append(c)
print(f"=== u100 cells available: {len(u)} over "
      f"{len(set(c['task'] for c in u))} distinct tasks, "
      f"variants {sorted(set(c['variant'] for c in u))} ===")
ua = defaultdict(lambda: [0, 0])
for c in u:
    a = ua[c["task"]]
    a[1] += 1
    a[0] += 1 if c["status"] == "pass" else 0
web, nonweb = [0, 0], [0, 0]
for t, (p, n) in ua.items():
    txt = prompt_of("u100", t)
    tgt = web if any(w in txt for w in ("html", "landing page", "website")) else nonweb
    tgt[0] += p
    tgt[1] += n
print(f"  BCF-web-floored (C7) tasks : {web[0]}/{web[1]} pass"
      + (f" = {100*web[0]/web[1]:.1f}%" if web[1] else ""))
print(f"  everything else            : {nonweb[0]}/{nonweb[1]} pass"
      + (f" = {100*nonweb[0]/nonweb[1]:.1f}%" if nonweb[1] else ""))
ut = sorted(ua)
if len(ut) >= 3:
    uf = [1 - ua[t][0] / ua[t][1] for t in ut]
    for name, xs in (("v1 rule score", [v1[("u100", t)]["score"] for t in ut]),
                     ("BCF rule_score", [bcf[("u100", t)]["bcf_score"] for t in ut])):
        rho = spearman(xs, uf)
        print(f"  spearman({name:15s}, u100 failure rate) = "
              + (f"{rho:+.3f}" if rho is not None else "n/a"))
