"""Cohort statistics, in integer cents."""


def median(values):
    """The median of `values`, in cents."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0
    if n % 2:
        return ordered[n // 2]
    # Even-sized: the midpoint of the two middle values.
    return (ordered[n // 2 - 1] + ordered[n // 2]) // 2
