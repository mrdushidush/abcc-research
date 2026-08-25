"""Feed the 149 corpus prompts to the vendored BCF rule scorer and compare it
to v1's.  BCF's call site is `router::assess_complexity_dual(prompt, ..)`
(mission.rs:268) -- one prompt, no title -- so that is what is fed.
"""
import json
import os
import subprocess
import statistics as st
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
EXE = os.path.join(HERE, "bcf_score", "target", "release", "bcf_score.exe")
CORPUS = os.path.join(ROOT, "corpus", "suites")

recs = []
for suite in ("q56", "u100", "k"):
    tdir = os.path.join(CORPUS, suite, "tasks")
    if not os.path.isdir(tdir):
        continue
    for tid in sorted(os.listdir(tdir)):
        p = os.path.join(tdir, tid, "prompt.txt")
        if not os.path.isfile(p):
            continue
        recs.append((f"{suite}/{tid}", open(p, encoding="utf-8").read()))

payload = "\u0000".join(f"{i}\u0001{t}" for i, t in recs)
out = subprocess.run([EXE], input=payload.encode("utf-8"),
                     stdout=subprocess.PIPE, check=True).stdout.decode("utf-8")
bcf = {}
for line in out.splitlines():
    if not line.strip():
        continue
    k, v = line.rsplit("\t", 1)
    bcf[k] = int(v)

v1 = {}
for line in open(os.path.join(HERE, "scores.jsonl"), encoding="utf-8"):
    line = line.strip()
    if not line.startswith("{"):
        continue
    r = json.loads(line)
    v1[f"{r['suite']}/{r['id']}"] = r

print(f"scored by BCF: {len(bcf)}   by v1: {len(v1)}")


def tier(s):
    if s >= 9:
        return "C9-C10 Expert"
    if s >= 7:
        return "C7-C8 Complex"
    if s >= 4:
        return "C4-C6 Moderate"
    return "C1-C3 Trivial"


print("\n=== BCF rule_score distribution (its own Tier::from_score) ===")
c = Counter(bcf.values())
print("  scores:", sorted(c.items()))
t = Counter(tier(s) for s in bcf.values())
for k in ["C1-C3 Trivial", "C4-C6 Moderate", "C7-C8 Complex", "C9-C10 Expert"]:
    print(f"  {k:16s} {t.get(k, 0):4d}")

print("\n=== per suite ===")
for suite in ("q56", "u100", "k"):
    ks = [k for k in bcf if k.startswith(suite + "/")]
    vals = [bcf[k] for k in ks]
    v1v = [v1[k]["score"] for k in ks if k in v1]
    print(f"  {suite:5s} n={len(ks):3d}  BCF min {min(vals)} p50 {st.median(vals)} "
          f"max {max(vals)}   |   v1 min {min(v1v)} p50 {st.median(v1v)} max {max(v1v)}")

print("\n=== BCF vs v1, same task ===")
diffs = []
for k in sorted(bcf):
    if k not in v1:
        continue
    d = bcf[k] - v1[k]["score"]
    diffs.append((d, k, bcf[k], v1[k]["score"]))
print(f"  n={len(diffs)}  mean(BCF - v1) = {st.mean(d for d, *_ in diffs):+.2f}  "
      f"median {st.median(d for d, *_ in diffs):+.1f}")
print(f"  BCF >= 7 (its Complex tier): {sum(1 for _, k, b, _ in diffs if b >= 7)}")
print(f"  v1  >= 7 (its 32K tier):     {sum(1 for _, k, _, a in diffs if a >= 7)}")
diffs.sort(reverse=True)
print("  largest disagreements (BCF - v1):")
for d, k, b, a in diffs[:12]:
    print(f"    {k:34s} BCF {b:2d}  v1 {a:4.1f}   diff {d:+.1f}")

# What in BCF's rules drives the difference?
print("\n=== BCF's two v1-absent rules, counted over the corpus ===")
web = [k for k, txt in recs if any(w in txt.lower()
                                   for w in ("html", "landing page", "website"))]
proj = [k for k, txt in recs if "project" in txt.lower()]
print(f"  prompts containing html/landing page/website -> score floored to 7: {len(web)}")
print(f"  prompts containing 'project' (in BCF's EXTREME list, +3): {len(proj)}")
overlap = set(web) & set(proj)
print(f"  both: {len(overlap)}")
print(f"  of the {len(web)} web-floored, BCF scores >= 7: "
      f"{sum(1 for k in web if bcf.get(k, 0) >= 7)}")
bysuite = defaultdict(int)
for k in web:
    bysuite[k.split('/')[0]] += 1
print(f"  web-floored by suite: {dict(bysuite)}")

with open(os.path.join(HERE, "bcf_scores.jsonl"), "w", encoding="utf-8", newline="\n") as f:
    for k in sorted(bcf):
        suite, tid = k.split("/", 1)
        f.write(json.dumps({"suite": suite, "id": tid, "bcf_score": bcf[k],
                            "bcf_tier": tier(bcf[k])}) + "\n")
