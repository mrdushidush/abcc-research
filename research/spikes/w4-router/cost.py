"""W4 item 2, move 3: the cost model, with ONE tier.

RESEARCH_BRIEF.md 11 asks for "per-task tokens and wall-clock across tiers, so
routing optimizes against a real objective."  There is exactly one tier -- one
model, one GPU, zero cloud spend, and co-residency is arithmetically impossible
on this card (W11 F275).  So the honest deliverable is two tables:

  (a) THE LOCAL RUNG'S REAL DISTRIBUTION -- what one attempt actually costs, in
      wall clock and in tokens, per suite and per arm.
  (b) THE PRICE OF EVERY ALTERNATIVE, in the same units, so the router can be
      shown what it is buying.  The only alternative it can actually afford is
      ANOTHER ATTEMPT ON THE SAME RUNG, so that one is priced against its yield:
      pass@k over the repeated cells, and the marginal pass bought per second by
      the 2nd, 3rd, 4th and 5th attempt.

pass@k is the unbiased estimator over n repeats with c passes:
    pass@k = 1 - C(n-c, k) / C(n, k)
which is exact here because the repeats are separate runs of the same cell.
"""
import json
import os
import glob
import math
import statistics as st

ROOT = r"D:\dev\ABCC_20_powerd_by_claudette"
SPIKE = os.path.join(ROOT, "research", "spikes", "w4-router")

# STRATIFY K BY MODEL AND BY ITERATION BUDGET.  Pooling them would be the memory's
# item-26 error twice over: the six `k-27b-*` families ran the 27B, and `w11-b12` /
# `w11-b20` ran the champion with the loop capped at 12 and 20 rounds, which caps
# occupancy and cost by construction.  The apples-to-apples local rung is the
# champion at `max_iterations = 40`; the 27B at the same budget is the escalation
# rung, and pricing the swap means comparing exactly those two.
POPS = (
    ("q56", ["runs/q56/w8-*"]),
    ("u100", ["runs/w8-*", "runs/prefix-invalid/w8-*"]),
    ("k-champ-40", ["runs/k-champ-r*/w8-*", "runs/w11-b40-r*/w8-*"]),
    ("k-27b-40", ["runs/k-27b-r*/w8-*", "runs/k-27b-t2400-r*/w8-*"]),
    ("k-champ-budget", ["runs/w11-b12-r*/w8-*", "runs/w11-b20-r*/w8-*"]),
)


def metric(cell, key):
    return cell.get("metrics", {}).get(key, {}).get("measured")


def load(pats):
    out = []
    for pat in pats:
        for run_dir in sorted(glob.glob(os.path.join(ROOT, pat))):
            cp = os.path.join(run_dir, "cells.jsonl")
            if not os.path.isfile(cp):
                continue
            run = os.path.basename(run_dir)
            family = os.path.basename(os.path.dirname(run_dir))
            for line in open(cp, encoding="utf-8"):
                c = json.loads(line)
                out.append({
                    "run": run, "family": family, "task": c["task"], "variant": c["variant"],
                    "status": c.get("status"),
                    "wall_clock_s": metric(c, "wall_clock_s"),
                    "tokens_in": metric(c, "tokens_in"),
                    "tokens_out": metric(c, "tokens_out"),
                    "iterations": metric(c, "iterations"),
                    "ttfvo_ms": metric(c, "ttfvo_ms"),
                })
    return out


def pct(vals, p):
    v = sorted(vals)
    k = min(len(v) - 1, int(round((p / 100.0) * (len(v) - 1))))
    return v[k]


def pass_at_k(n, c, k):
    if k > n:
        return None
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def main():
    print("=" * 78)
    print("(a) THE LOCAL RUNG: what one attempt costs, per suite and per arm")
    print("=" * 78)
    print("{:<6} {:<20} {:>5} {:>7} {:>7} {:>7} {:>8} {:>8} {:>7}".format(
        "suite", "arm", "n", "wall50", "wall90", "wallmax", "tok_in50", "tok_out50", "iter50"))
    all_cells = {}
    for name, pats in POPS:
        cells = load(pats)
        all_cells[name] = cells
        for arm in sorted({c["variant"] for c in cells}):
            v = [c for c in cells if c["variant"] == arm and c["wall_clock_s"]]
            if len(v) < 5:
                continue
            w = [c["wall_clock_s"] for c in v]
            ti = [c["tokens_in"] for c in v if c["tokens_in"]]
            to = [c["tokens_out"] for c in v if c["tokens_out"]]
            it = [c["iterations"] for c in v if c["iterations"]]
            print("{:<6} {:<20} {:>5} {:>7.1f} {:>7.1f} {:>7.1f} {:>8.0f} {:>8.0f} {:>7.0f}".format(
                name, arm, len(v), pct(w, 50), pct(w, 90), max(w),
                pct(ti, 50) if ti else 0, pct(to, 50) if to else 0, pct(it, 50) if it else 0))

    print()
    print("=" * 78)
    print("(b) THE ONLY ALTERNATIVE RUNG THE BUDGET ALLOWS: another attempt")
    print("=" * 78)
    print("pass@k over repeated cells, control arm only (an interfered arm prices a")
    print("different experiment). k attempts cost k x the per-attempt wall clock.")
    for name in ("q56", "u100", "k-champ-40", "k-27b-40"):
        cells = [c for c in all_cells[name] if c["variant"] == "control"]
        by_task = {}
        for c in cells:
            by_task.setdefault(c["task"], []).append(c)
        reps = sorted({len(v) for v in by_task.values()})
        n_rep = max(set(len(v) for v in by_task.values()), key=lambda n:
                    sum(1 for v in by_task.values() if len(v) == n))
        tasks = {t: v for t, v in by_task.items() if len(v) == n_rep}
        if not tasks:
            continue
        wall = [c["wall_clock_s"] for v in tasks.values() for c in v if c["wall_clock_s"]]
        mean_wall = st.fmean(wall)
        print("\n  {}: {} tasks at exactly n={} repeats (repeat counts seen: {})".format(
            name, len(tasks), n_rep, reps))
        print("     mean attempt wall clock {:.1f} s   median {:.1f} s".format(
            mean_wall, pct(wall, 50)))
        prev = None
        for k in range(1, min(n_rep, 6) + 1):
            vals = [pass_at_k(n_rep, sum(1 for c in v if c["status"] == "pass"), k)
                    for v in tasks.values()]
            m = st.fmean(vals)
            line = "     pass@{}: {:.1%}   cumulative cost {:.0f} s/task".format(
                k, m, k * mean_wall)
            if prev is not None:
                gain = m - prev
                line += "   marginal +{:.1%} for {:.1f} s  = {:.3f} pp/min".format(
                    gain, mean_wall, gain * 100 * 60 / mean_wall)
            print(line)
            prev = m
        # THE CIRCUIT-BREAKER NUMBER.  pass@k above is the value of a retry budget decided
        # BEFORE the first attempt.  What a breaker needs is the value of the NEXT attempt
        # GIVEN the ones already burnt -- and those failures are evidence about which task
        # this is.  With p_t the task's empirical pass rate and the task mix as the prior,
        #     P(pass at k+1 | first k all failed) = sum_t p_t (1-p_t)^k / sum_t (1-p_t)^k
        ps = [sum(1 for c in v if c["status"] == "pass") / len(v) for v in tasks.values()]
        print("     P(next attempt passes | k already failed), updating on the failures:")
        for k in range(0, min(n_rep, 5)):
            num = sum(p * (1 - p) ** k for p in ps)
            den = sum((1 - p) ** k for p in ps)
            print("        k={}: {:.1%}{}".format(
                k, num / den if den else float("nan"),
                "   <- the unconditional pass rate" if k == 0 else ""))
        never = [t for t, v in tasks.items() if not any(c["status"] == "pass" for c in v)]
        always = [t for t, v in tasks.items() if all(c["status"] == "pass" for c in v)]
        print("     tasks that NEVER pass in {} tries: {} ({})".format(
            n_rep, len(never), ", ".join(sorted(never)) or "-"))
        print("     tasks that ALWAYS pass: {} of {}  -> the retry budget only ever".format(
            len(always), len(tasks)))
        print("     matters on the remaining {}".format(len(tasks) - len(always) - len(never)))

    print()
    print("=" * 78)
    print("(c) THE PRICE LIST: every alternative to 'try again', in the same units")
    print("=" * 78)
    q56c = [c for c in all_cells["q56"] if c["variant"] == "control" and c["wall_clock_s"]]
    kc = [c for c in all_cells["k-champ-40"] if c["wall_clock_s"]]
    k27 = [c for c in all_cells["k-27b-40"] if c["wall_clock_s"]]
    mq = st.fmean([c["wall_clock_s"] for c in q56c])
    mk = st.fmean([c["wall_clock_s"] for c in kc])
    # Quote the MEDIAN too: the mean is dragged by cells that ran to the 600 s / 2,400 s
    # timeout, so a price expressed in mean-attempts flatters the swap.
    dq = pct([c["wall_clock_s"] for c in q56c], 50)
    dk = pct([c["wall_clock_s"] for c in kc], 50)
    print("  reference attempt cost: Q56 control mean {:.1f} s / median {:.1f} s;"
          "  K mean {:.1f} s / median {:.1f} s".format(mq, dq, mk, dk))
    for label, secs, src in (
        ("model swap, round trip", 23.77, "W2 F79"),
        ("model swap, re-measured", 26.3, "W11 F284"),
    ):
        print("  {:<28} {:>7.2f} s = {:.2f} median Q56 attempts / {:.2f} median K   [{}]".format(
            label, secs, secs / dq, secs / dk, src))
    print("  {:<28} {:>7} x decode on the bigger model            [W11 F284]".format(
        "then every token costs", "4.6"))
    print("  {:<28} {:>7} x a warm turn (full cold prefill)       [W11 item 2]".format(
        "head rewrite of the prompt", "4.60"))
    print("  {:<28} saves {:>3}% of TTFT, and ONE token at the front".format(
        "prefix cache, left intact", "79.7"))
    print("  {:<28} annihilates it                                [W2 F81]".format(""))
    print("  {:<28} impossible: 1,210 MiB free vs a 4.41 GB model [W11 F275]".format(
        "second model co-resident"))
    print("  {:<28} not a tier: zero cloud spend is standing".format("a cloud rung"))
    print()
    print("  THE ONE COMPARISON A ROUTER CAN ACTUALLY MAKE, in points of pass rate per minute:")
    swap = 26.3 + 5.2 * dq   # W11 F284 + W1 F87/F88: the 27B ran the campaign at 5.2x
    print("     retry once on the same rung: +6.4 pp for {:.1f} s = {:.1f} pp/min".format(
        dq, 6.4 * 60 / dq))
    print("     swap to the 27B and attempt : W1 F87/F88 measured it LEVEL on verdicts (8/9),")
    print("        so <=0 pp, for 26.3 s of swap plus 5.2x the attempt = {:.1f} s "
          "= {:.1f} retries".format(swap, swap / dq))
    print()
    print("  AND THE SAME COMPARISON RE-MEASURED HEAD TO HEAD ON THE HARD SUITE (K, 3 tasks,")
    print("  18 cells each, both at max_iterations=40, same fixtures, same verifier):")
    d27 = pct([c["wall_clock_s"] for c in k27], 50)
    print("     champion  median attempt {:>7.1f} s   timeouts {}".format(
        dk, sum(1 for c in kc if c["status"] == "timeout")))
    print("     27B       median attempt {:>7.1f} s   timeouts {}   = {:.2f}x the champion".format(
        d27, sum(1 for c in k27 if c["status"] == "timeout"), d27 / dk))

    out = os.path.join(SPIKE, "cost.jsonl")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        for name, cells in all_cells.items():
            for c in cells:
                c["pop"] = name
                fh.write(json.dumps(c) + "\n")
    print("\nwrote {}".format(out))


if __name__ == "__main__":
    main()
