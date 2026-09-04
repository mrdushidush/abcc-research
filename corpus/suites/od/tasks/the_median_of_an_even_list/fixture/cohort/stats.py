"""Cohort statistics, in integer cents."""


def median(values):
    """The median of `values`, in cents."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0
    return ordered[n // 2]
