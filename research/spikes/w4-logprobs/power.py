"""OQ-W4-12, answered with arithmetic instead of another campaign.

Item 3 closed with an open question it could not answer from its own data:
*how many tasks would resolve a real +0.05 AUC difference, and can any corpus
here be that big?*  Item 4 inherits it, because the dry run on 43 cells with 6
failures produced ~55 candidate signals of which **not one** had an interval
excluding the coin — and "we could not resolve it" is only useful if you can
say what would have.

This is deliberately the OPTIMISTIC bound.  Hanley-McNeil gives the standard
error of an AUC under independent observations; the real design is five repeats
over 56 tasks, which is 56 clusters, so the true interval is WIDER than
anything printed here by a design effect this does not attempt to estimate.  If
a number here already says "impossible on this corpus", clustering only makes it
more so.

Two questions, both at 95%:
  1. How many failures to separate a signal of true AUC A from the coin?
  2. How many to separate two signals whose true AUCs differ by 0.05 -- the
     comparison F379 could not make and the one that decides "is the logprob
     better than the free counter?"

For (2) the paired comparison shares the same cases, which helps; the
correlation between two rank-based scores on the same rows is high, so the
variance of the difference is scaled by 2(1-rho).  Both a generous rho = 0.8
and an ungenerous rho = 0.5 are printed, because the answer should not rest on
a guess about it.
"""
import math

Q56_FAIL_RATE = 0.12   # 88.2% pass on the control arm (F373)


def hanley_se(a, n1, n0):
    """SE of an AUC estimate: n1 positives (failures), n0 negatives."""
    q1 = a / (2.0 - a)
    q2 = 2.0 * a * a / (1.0 + a)
    var = (a * (1 - a) + (n1 - 1) * (q1 - a * a) + (n0 - 1) * (q2 - a * a)) / (n1 * n0)
    return math.sqrt(var)


def cells_for(a, target, rho=None, fail_rate=Q56_FAIL_RATE, cap=4_000_000):
    """Smallest cell count whose 95% half-width beats `target`.

    `rho=None` -> the signal against the coin. `rho` set -> the paired
    difference between two signals of similar AUC on the same cases.
    """
    n = 20
    while n < cap:
        n1 = max(2, int(round(n * fail_rate)))
        n0 = n - n1
        if n0 < 2:
            n += 10
            continue
        se = hanley_se(a, n1, n0)
        if rho is not None:
            se = se * math.sqrt(2.0 * (1.0 - rho))
        if 1.96 * se < target:
            return n, n1
        n = int(n * 1.05) + 1
    return None, None


def main():
    print("Assumptions: Q56 control fail rate %.0f%%, 95%% intervals, INDEPENDENT "
          "cells (the real design has 56 clusters, so these are floors)."
          % (100 * Q56_FAIL_RATE))

    print("\n1) Separating one signal from the coin (interval must exclude 0.50)")
    print("%-12s %14s %14s %16s" % ("true AUC", "cells needed", "failures", "Q56 repeats"))
    for a in (0.60, 0.65, 0.70, 0.75, 0.80):
        n, n1 = cells_for(a, a - 0.5)
        print("%-12.2f %14s %14s %16s"
              % (a, n, n1, "%.1f" % (n / 56.0) if n else "-"))

    print("\n2) Separating TWO signals 0.05 apart -- 'is the logprob better than "
          "the free counter?'")
    print("%-12s %8s %14s %14s %16s" %
          ("true AUC", "rho", "cells needed", "failures", "Q56 repeats"))
    for a in (0.65, 0.70):
        for rho in (0.8, 0.5):
            n, n1 = cells_for(a, 0.05, rho=rho)
            print("%-12.2f %8.1f %14s %14s %16s"
                  % (a, rho, n, n1, "%.0f" % (n / 56.0) if n else "-"))

    print("\n3) What this project actually has")
    for name, n in (("one Q56 control run", 56),
                    ("the three recorded control runs", 168),
                    ("this campaign, 5 repeats", 280),
                    ("every control cell on disk (W4 item 3's population)", 378)):
        n1 = int(round(n * Q56_FAIL_RATE))
        se = hanley_se(0.70, max(2, n1), n - max(2, n1))
        print("  %-52s n=%-5d failures~%-4d 95%% half-width at AUC 0.70 = +/-%.3f"
              % (name, n, n1, 1.96 * se))


if __name__ == "__main__":
    main()
