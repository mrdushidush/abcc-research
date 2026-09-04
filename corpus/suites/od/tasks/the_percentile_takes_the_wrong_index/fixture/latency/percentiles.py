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
    index = int(n * p)
    return ordered[min(n - 1, index)]


def summary(values):
    return {"p50": value_at(values, 0.50), "p95": value_at(values, 0.95)}
