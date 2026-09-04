"""Cohort statistics, in integer cents."""


def median(values):
    """The median of `values`, in cents."""
    ordered = sorted(values)
    n = len(ordered)
    if n == 0:
        return 0
    if n % 2:
        return ordered[n // 2]
    # Even-sized: the midpoint of the two middle values, rounded HALF UP
    # (docs/median.md). Truncating biases every even cohort downward.
    lower, upper = ordered[n // 2 - 1], ordered[n // 2]
    return (lower + upper + 1) // 2
