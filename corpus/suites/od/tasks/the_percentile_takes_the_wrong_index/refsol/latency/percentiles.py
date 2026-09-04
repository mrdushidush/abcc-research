"""Percentiles, by nearest rank.

Milliseconds, integers, no interpolation: the reported value is always one of
the observations.
"""

import math


def value_at(values, p):
    """The `p` percentile of `values`, by nearest rank."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0
    # Nearest rank: the smallest rank r with r/n >= p, and ranks count from 1
    # (docs/percentiles.md). `int(n * p)` is that rank only when n * p is a
    # whole number, and one short of it every other time.
    index = math.ceil(n * p) - 1
    return ordered[max(0, min(n - 1, index))]


def summary(values):
    return {"p50": value_at(values, 0.50), "p95": value_at(values, 0.95)}
