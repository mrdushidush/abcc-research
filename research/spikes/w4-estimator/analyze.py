"""W4 item 3 analysis: what a pre-dispatch estimate is worth, and what it costs.

Two axes, both required, because item 2 (F374) changed what the estimator has to
beat.  An a-priori score now competes with an OBSERVED first failure that is
free, exact, and worth 44.6 points -- and that arrives about 19 seconds after
dispatch, which is Q56's median attempt.  So a model estimator has to be better
than the free features AND cheaper than just running the task.

Metrics
-------
rho   Spearman against the CONTROL-arm failure rate, task level -- the identical
      construction item 1 used, so +0.219 (BCF rule_score), +0.187 (prompt word
      count) and +0.101 (v1 score) are directly comparable numbers and not
      re-derived ones.

AUC   Mann-Whitney: the probability that a randomly chosen task which failed at
      least once ranks harder than a randomly chosen task that never failed,
      ties counted as half.  0.5 is a coin.  This is here because rho is a weak
      instrument on this population: 40 of 56 Q56 tasks pass 5/5, so most of the
      outcome column is one value and a rank correlation over it is dominated by
      ties.  AUC asks the question routing actually asks -- can this signal put
      the 16 tasks that ever fail above the 40 that never do?

Sign convention: every predictor is oriented so that HIGHER MEANS HARDER before
rho and AUC are computed, so a useful signal is positive in both columns.  The
`pass_pct` arms predict success, so they are negated, and that negation is
printed next to them.
"""
import json
import math
import os
import random
import statistics as st
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


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


def auc(scores, labels):
    """P(score of a positive > score of a negative), ties = 0.5."""
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None, len(pos), len(neg)
    w = sum(1.0 if a > b else 0.5 if a == b else 0.0 for a in pos for b in neg)
    return w / (len(pos) * len(neg)), len(pos), len(neg)


def pct(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1))))]


tasks = {(r["suite"], r["id"]): r for r in jsonl(os.path.join(HERE, "tasks.jsonl"))}
est = list(jsonl(os.path.join(HERE, "estimates.jsonl")))

ARM_ORDER = ["v1_verbatim", "v1_schema", "v1_schema_rf", "pass_pct",
             "v1_nothink", "pass_pct_nothink"]
# arms whose value predicts SUCCESS, so it is negated to point at difficulty
INVERTED = {"pass_pct", "pass_pct_nothink"}

# rep 0 is the run every table below uses; later reps are the repeatability probe
by = defaultdict(dict)          # (suite,id) -> arm -> value   (rep 0)
reps = defaultdict(list)        # (suite,id,arm) -> [values]
for r in est:
    k = (r["suite"], r["id"])
    if r["rep"] == 0:
        by[k][r["arm"]] = r
    reps[(r["suite"], r["id"], r["arm"])].append(r)

print("=== 0. what ran ===")
print("  estimator calls: %d over %d tasks x %d arms x reps %s"
      % (len(est), len(set((r["suite"], r["id"]) for r in est)),
         len(set(r["arm"] for r in est)), sorted(set(r["rep"] for r in est))))
bad = [r for r in est if r["value"] is None]
print("  calls with no usable value: %d" % len(bad))
for r in bad[:12]:
    print("     %s/%s %s rep%d  finish=%s parse=%s out=%s"
          % (r["suite"], r["id"], r["arm"], r["rep"], r["finish_reason"],
             r["parse_error"], r["completion_tokens"]))
print()

# ------------------------------------------------------------------ A. cost
print("=== A. what an estimate COSTS, against Q56's 19.1 s median attempt (F372) ===")
print("  %-17s %5s  %7s %7s %7s  %7s  %7s  %6s" %
      ("arm", "n", "p50 s", "p90 s", "max s", "p50 out", "p50 thk", "fail"))
for arm in ARM_ORDER:
    rows = [r for r in est if r["arm"] == arm and r["rep"] == 0]
    if not rows:
        continue
    w = [r["wall_s"] for r in rows]
    o = [r["completion_tokens"] or 0 for r in rows]
    t = [r["reasoning_chars"] for r in rows]
    nf = sum(1 for r in rows if r["value"] is None)
    print("  %-17s %5d  %7.2f %7.2f %7.2f  %7d  %7d  %6d" %
          (arm, len(rows), pct(w, 50), pct(w, 90), max(w), pct(o, 50), pct(t, 50), nf))
print()
print("  truncation rate if max_tokens had been lower (completion_tokens >= budget):")
for arm in ARM_ORDER:
    rows = [r for r in est if r["arm"] == arm and r["rep"] == 0]
    if not rows:
        continue
    line = "  %-17s" % arm
    for budget in (300, 1000, 2000, 3000, 6000):
        n = sum(1 for r in rows if (r["completion_tokens"] or 0) >= budget)
        line += "  %d@%d" % (n, budget)
    print(line)
print()

# ------------------------------------------- B. does the estimate discriminate?
print("=== B. the estimate's own distribution -- can it separate anything? ===")
for arm in ARM_ORDER:
    vals = [r["value"] for r in est if r["arm"] == arm and r["rep"] == 0
            and r["value"] is not None]
    if not vals:
        continue
    d = defaultdict(int)
    for v in vals:
        d[v] += 1
    print("  %-17s n=%d  distinct=%d  %s" %
          (arm, len(vals), len(d),
           "  ".join("%s:%d" % (k, v) for k, v in sorted(d.items()))))
print()

# --------------------------------------------------- C. the comparison table
def free_features(rows):
    return [
        ("v1 rule score",   [r["v1_score"] for r in rows]),
        ("BCF rule_score",  [r["bcf_score"] for r in rows]),
        ("prompt words",    [r["prompt_words"] for r in rows]),
        ("prompt bytes",    [r["prompt_bytes"] for r in rows]),
        ("fixture bytes",   [r["fixture_bytes"] for r in rows]),
        ("fixture files",   [r["fixture_files"] for r in rows]),
    ]


def cv_group(rows, key, folds=7):
    """Cross-validated group encoding: predict a task's failure rate from the mean
    failure rate of OTHER tasks sharing its `kind` (or `lang`), fitted on the
    other folds only.

    ⚠ The obvious version -- leave-one-out, (S_g - x_i) / (n_g - 1) -- is not
    honest here.  Within one group that quantity is a strictly DECREASING
    function of x_i, so it is perfectly inversely ranked with the value it is
    predicting, by construction.  On a suite where every task shares one kind
    (u100, k) it returns rho = -1.000 with no signal in the data at all.  Folds
    fix it: a held-out task's own value never enters the encoding, and tasks in
    the same fold and group share one predicted value, so no inverse ranking can
    be manufactured.  Fold assignment is by position in a deterministic sort, so
    the number is reproducible.

    Returns None for a task whose group is absent from the training folds."""
    idx = {id(r): i for i, r in enumerate(rows)}
    out = []
    for r in rows:
        i = idx[id(r)]
        train = [q for j, q in enumerate(rows) if j % folds != i % folds]
        tot = defaultdict(lambda: [0.0, 0])
        for q in train:
            a = tot[q[key]]
            a[0] += 1 - q["control_rate"]
            a[1] += 1
        g = tot.get(r[key])
        out.append(g[0] / g[1] if g and g[1] else None)
    return out


def group_permutation_p(rows, key, trials=20000, seed=20260825):
    """Does `key` explain more of the failure-rate spread than a random grouping
    of the same shape?  Statistic: the between-group sum of squares of the failure
    rate.  The null shuffles the labels, keeping the group sizes exactly.  Returns
    (observed, p) where p is the share of shuffles at least as extreme."""
    vals = [1 - r["control_rate"] for r in rows]
    labels = [r[key] for r in rows]
    if len(set(labels)) < 2:
        return None, None

    def between(ls):
        grand = st.mean(vals)
        tot = defaultdict(list)
        for l, v in zip(ls, vals):
            tot[l].append(v)
        return sum(len(v) * (st.mean(v) - grand) ** 2 for v in tot.values())

    obs = between(labels)
    rnd = random.Random(seed)
    shuf = list(labels)
    hits = 0
    for _ in range(trials):
        rnd.shuffle(shuf)
        if between(shuf) >= obs:
            hits += 1
    return obs, (hits + 1) / (trials + 1)


for suite in ("q56", "u100", "k"):
    rows = [t for t in tasks.values() if t["suite"] == suite]
    if len(rows) < 10:
        print("=== C. %s: %d tasks, too few for a rank statistic -- values only ==="
              % (suite, len(rows)))
        for t in rows:
            k = (t["suite"], t["id"])
            got = {a: (by[k].get(a) or {}).get("value") for a in ARM_ORDER}
            print("  %-32s fail=%.2f  %s" % (t["id"], 1 - t["control_rate"], got))
        print()
        continue

    fail = [1 - t["control_rate"] for t in rows]
    ever = [t["control_pass"] < t["control_n"] for t in rows]
    print("=== C. %s: %d tasks, %d of them fail at least once in the control arm ==="
          % (suite, len(rows), sum(ever)))
    print("  %-28s %8s  %8s   %s" % ("predictor (higher = harder)", "rho", "AUC", "n"))

    feats = list(free_features(rows))
    for key in ("kind", "lang"):
        # A one-group column cannot rank anything.  Any number a CV encoding
        # produces there is a fact about the folds, so do not print one.
        if len(set(r[key] for r in rows)) < 2:
            continue
        cv = cv_group(rows, key)
        if all(v is not None for v in cv) and len(set(cv)) > 1:
            feats.append(("%s (7-fold CV encoding)" % key, cv))

    for arm in ARM_ORDER:
        vs, fs, es = [], [], []
        for t, f, e in zip(rows, fail, ever):
            v = (by[(t["suite"], t["id"])].get(arm) or {}).get("value")
            if v is None:
                continue
            vs.append(-v if arm in INVERTED else v)
            fs.append(f)
            es.append(e)
        if len(vs) < 3:
            continue
        rho = spearman(vs, fs)
        a, npos, nneg = auc(vs, es)
        feats.append(("MODEL %s%s" % (arm, " (negated)" if arm in INVERTED else ""),
                      None))
        feats[-1] = (feats[-1][0], (vs, fs, es))

    for name, payload in feats:
        if isinstance(payload, tuple):
            vs, fs, es = payload
        else:
            vs, fs, es = payload, fail, ever
        rho = spearman(vs, fs)
        a, npos, nneg = auc(vs, es)
        print("  %-28s %8s  %8s   %d" %
              (name,
               "%+.3f" % rho if rho is not None else "n/a",
               "%.3f" % a if a is not None else "n/a",
               len(vs)))
    for key in ("kind", "lang"):
        obs, p = group_permutation_p(rows, key)
        if obs is None:
            print("  permutation test on %-5s: only one group in this suite" % key)
        else:
            print("  permutation test on %-5s: between-group SS %.4f, p = %.3f "
                  "against label shuffles that keep the group sizes" % (key, obs, p))
    print()

# ------------------------------------------------- D. arm-vs-arm disagreement
print("=== D. is the estimate a property of the task, or of how it was asked? ===")
pairs = [("v1_schema", "v1_schema_rf", "emission order: score first vs reasoning first"),
         ("v1_schema", "v1_nothink", "the reasoning trace: on vs off, same schema"),
         ("v1_verbatim", "v1_schema", "free text vs constrained, same rubric"),
         ("pass_pct", "pass_pct_nothink", "the reasoning trace on the pass estimate")]
for a1, a2, why in pairs:
    d, same = [], 0
    for k, arms in by.items():
        v1v = (arms.get(a1) or {}).get("value")
        v2v = (arms.get(a2) or {}).get("value")
        if v1v is None or v2v is None:
            continue
        d.append(v2v - v1v)
        same += 1 if v1v == v2v else 0
    if not d:
        continue
    print("  %-16s vs %-16s  n=%d  identical %d (%.0f%%)  mean shift %+.2f  "
          "range %+d..%+d   [%s]"
          % (a1, a2, len(d), same, 100.0 * same / len(d), st.mean(d),
             min(d), max(d), why))
print()

# ------------------------------------------------------- E. repeatability
multi = {k: v for k, v in reps.items() if len(v) > 1}
if multi:
    print("=== E. repeatability at temperature 0.0 ===")
    print("  !! Two different facts, kept apart: whether the VALUE moved between two")
    print("  identical calls, and whether the call ANSWERED at all.  Pooling them")
    print("  reports a failed call as a changed reading.")
    print("  %-17s %8s %8s %8s   %-18s %s"
          % ("arm", "both ok", "same", "max |d|", "deltas", "answer flipped"))
    for arm in ARM_ORDER:
        both, same, deltas, flipped = 0, 0, [], 0
        for (suite, tid, a), rs in multi.items():
            if a != arm:
                continue
            vals = [r["value"] for r in sorted(rs, key=lambda r: r["rep"])]
            if any(v is None for v in vals):
                if not all(v is None for v in vals):
                    flipped += 1
                continue
            both += 1
            if len(set(vals)) == 1:
                same += 1
            else:
                deltas.append(vals[-1] - vals[0])
        if not both and not flipped:
            continue
        print("  %-17s %8d %8d %8s   %-18s %d"
              % (arm, both, same,
                 max(abs(d) for d in deltas) if deltas else 0,
                 sorted(deltas) if deltas else "-", flipped))
    print()
    print("  A no-think arm is a deterministic function of its input at temperature 0;")
    print("  every arm that runs a reasoning trace is not, and the arm with the longest")
    print("  trace is the least stable.")
    print()


# ------------------------------------------------ F. calibration, not ranking
print("=== F. calibration: the estimate against the base rate it is estimating ===")
for suite in ("q56", "u100", "k"):
    rows = [t for t in tasks.values() if t["suite"] == suite]
    if not rows:
        continue
    base = sum(t["control_pass"] for t in rows) / sum(t["control_n"] for t in rows)
    print("  -- %s: measured control pass rate %.1f%% over %d cells"
          % (suite, 100 * base, sum(t["control_n"] for t in rows)))
    for arm in ("pass_pct", "pass_pct_nothink"):
        vs = [((by[(t["suite"], t["id"])].get(arm) or {}).get("value"),
               t["control_rate"]) for t in rows]
        vs = [(v, c) for v, c in vs if v is not None]
        if not vs:
            continue
        pred = st.mean(v for v, _ in vs)
        print("     %-17s mean estimate %5.1f%%  (population error %+.1f pp)"
              % (arm, pred, pred - 100 * base))
        buckets = defaultdict(lambda: [0, 0])
        for v, c in vs:
            b = buckets[10 * (v // 10)]
            b[0] += c
            b[1] += 1
        for b in sorted(buckets):
            s, n = buckets[b]
            print("        estimate %3d-%3d  n=%2d  actual pass %.1f%%"
                  % (b, b + 9, n, 100 * s / n))
print()

# -------------------------------- G. what could a perfect estimate even buy?
print("=== G. the ceiling: what a PERFECT a-priori oracle would buy over reacting ===")
for suite in ("q56", "u100", "k"):
    rows = [t for t in tasks.values() if t["suite"] == suite]
    if not rows:
        continue
    n = len(rows)
    p_fail_first = 1 - sum(t["control_pass"] for t in rows) / sum(t["control_n"]
                                                                 for t in rows)
    ever = sum(1 for t in rows if t["control_pass"] < t["control_n"])
    print("  -- %s (%d tasks, %d ever fail, first-attempt failure rate %.1f%%)"
          % (suite, n, ever, 100 * p_fail_first))
    print("     REACTIVE  'attempt once, retry once if it failed':")
    print("        attempts per task = 1 + %.3f = %.3f, and the retry lands on the "
          "failures with certainty" % (p_fail_first, 1 + p_fail_first))
    print("     PREDICTIVE 'a PERFECT oracle names the %d tasks that ever fail and "
          "pre-allocates 2':" % ever)
    print("        attempts per task = 1 + %d/%d = %.3f, plus one estimator call on "
          "all %d" % (ever, n, 1 + ever / n, n))
    print("        -> the oracle spends MORE attempts (%.3f vs %.3f) and buys no "
          "outcome the reactive policy misses," % (1 + ever / n, 1 + p_fail_first))
    print("           because a task that fails is identified by failing.  The "
          "estimator's ceiling is negative before its own cost is counted.")
print()

# --------------- H. the estimator against the budget it exists to allocate
print("=== H. one pass over the corpus: the estimator's bill vs the retries' bill ===")
for suite in ("q56", "u100", "k"):
    rows = [t for t in tasks.values() if t["suite"] == suite]
    if not rows:
        continue
    n = len(rows)
    pf = 1 - sum(t["control_pass"] for t in rows) / sum(t["control_n"] for t in rows)
    med = {"q56": 19.1, "u100": 13.9, "k": 110.8}[suite]   # F372's medians
    retry = n * pf * med
    print("  -- %s: %d tasks, first-attempt failure %.1f%%, median attempt %.1f s"
          % (suite, n, 100 * pf, med))
    print("     REACTIVE retry bill for the whole corpus: %.0f tasks x %.1f s = %.0f s"
          % (n * pf, med, retry))
    for arm in ARM_ORDER:
        w = [r["wall_s"] for r in est
             if r["rep"] == 0 and r["arm"] == arm and r["suite"] == suite]
        if not w:
            continue
        tot = sum(w)
        print("     %-17s bill %7.0f s  = %5.2fx the retries it would be allocating"
              % (arm, tot, tot / retry if retry else float("nan")))
print()

# ------------------------------------------- I. are any of these differences real?
print("=== I. bootstrap: is any predictor distinguishable from any other at n=56? ===")
print("  10,000 resamples of TASKS with replacement, fixed seed.  A paired")
print("  difference whose 95% interval spans 0 is not a difference.")
for suite in ("q56",):
    rows = [t for t in tasks.values() if t["suite"] == suite]
    ever = [t["control_pass"] < t["control_n"] for t in rows]
    cand = {"BCF rule_score": [t["bcf_score"] for t in rows],
            "prompt words": [t["prompt_words"] for t in rows],
            "prompt bytes": [t["prompt_bytes"] for t in rows]}
    for arm in ARM_ORDER:
        v = []
        for t in rows:
            x = (by[(t["suite"], t["id"])].get(arm) or {}).get("value")
            v.append(None if x is None else (-x if arm in INVERTED else x))
        cand["MODEL " + arm] = v

    rnd = random.Random(20260826)
    N = len(rows)
    draws = [[rnd.randrange(N) for _ in range(N)] for _ in range(10000)]

    def boot_auc(vals):
        out = []
        for d in draws:
            s = [vals[i] for i in d if vals[i] is not None]
            l = [ever[i] for i in d if vals[i] is not None]
            a, _, _ = auc(s, l)
            if a is not None:
                out.append(a)
        out.sort()
        return out

    b = {k: boot_auc(v) for k, v in cand.items()}
    print("  %-28s %8s  %s" % ("predictor", "AUC", "95% interval"))
    for k, v in cand.items():
        pt, _, _ = auc([x for x in v if x is not None],
                       [e for x, e in zip(v, ever) if x is not None])
        lo, hi = b[k][int(0.025 * len(b[k]))], b[k][int(0.975 * len(b[k]))]
        print("  %-28s %8.3f  [%.3f, %.3f]" % (k, pt, lo, hi))
    print()
    print("  paired differences against the best FREE feature (prompt bytes):")
    base = cand["prompt bytes"]
    for k, v in cand.items():
        if k == "prompt bytes":
            continue
        diffs = []
        for d in draws:
            s1 = [(v[i], ever[i]) for i in d if v[i] is not None]
            s2 = [(base[i], ever[i]) for i in d if base[i] is not None]
            a1, _, _ = auc([x for x, _ in s1], [e for _, e in s1])
            a2, _, _ = auc([x for x, _ in s2], [e for _, e in s2])
            if a1 is not None and a2 is not None:
                diffs.append(a1 - a2)
        diffs.sort()
        lo, hi = diffs[int(0.025 * len(diffs))], diffs[int(0.975 * len(diffs))]
        mid = diffs[len(diffs) // 2]
        verdict = "SPANS 0" if lo <= 0 <= hi else "excludes 0"
        print("  %-28s %+.3f  [%+.3f, %+.3f]  %s" % (k, mid, lo, hi, verdict))
print()
