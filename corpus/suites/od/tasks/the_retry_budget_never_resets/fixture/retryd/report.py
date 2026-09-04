"""The retry SLA check.

We promise that most failures get at least one retry. The number is a floor on
the whole day's failures, deliberately: a rate computed over only the failures
we chose to retry would be 100% by construction and would report nothing.
"""

MIN_RETRY_RATE = 0.70


class RetrySLABreached(Exception):
    pass


def retry_rate(retried, dropped):
    total = len(retried) + len(dropped)
    if total == 0:
        return 1.0
    return len(retried) / total


def check(retried, dropped):
    rate = retry_rate(retried, dropped)
    if rate < MIN_RETRY_RATE:
        raise RetrySLABreached(
            "retry rate {:.0%} is below the {:.0%} floor: {} of {} failures were never "
            "retried".format(rate, MIN_RETRY_RATE, len(dropped), len(retried) + len(dropped))
        )
    return rate
