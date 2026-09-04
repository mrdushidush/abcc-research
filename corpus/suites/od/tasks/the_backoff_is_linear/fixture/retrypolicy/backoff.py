"""The backoff schedule."""

BASE_S = 1
MAX_S = 60


def delay(attempt):
    """Seconds to wait before attempt number `attempt`, counting from 1."""
    return BASE_S * attempt


def schedule(attempts):
    return [delay(n) for n in range(1, attempts + 1)]


def total_wait(attempts):
    return sum(schedule(attempts))
