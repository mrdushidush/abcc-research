"""The backoff schedule."""

BASE_S = 1
MAX_S = 60


def delay(attempt):
    """Seconds to wait before attempt number `attempt`, counting from 1.

    Doubling, and never longer than `MAX_S` (docs/backoff.md): an unbounded
    doubling is how a queue that is only briefly unhealthy ends up idle for
    hours.
    """
    return min(BASE_S * 2 ** (attempt - 1), MAX_S)


def schedule(attempts):
    return [delay(n) for n in range(1, attempts + 1)]


def total_wait(attempts):
    return sum(schedule(attempts))
