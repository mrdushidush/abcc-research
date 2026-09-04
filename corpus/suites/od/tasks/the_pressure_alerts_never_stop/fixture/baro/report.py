"""The batch report, and the circuit breaker on alerting.

`MAX_ALERTS` is a breaker, not a policy. If a whole batch is out of range the
batch is wrong, not the world, and paging someone per reading buries the one
alert that matters.
"""

from . import alerts

MAX_ALERTS = 5


class AlertStorm(Exception):
    pass


def summarise(readings):
    below, above = alerts.out_of_range(readings)
    if len(below) + len(above) > MAX_ALERTS:
        raise AlertStorm(
            "{} of {} readings are outside {}-{} cKPa -- the batch is wrong, not the "
            "weather".format(
                len(below) + len(above), len(readings), alerts.MIN_CKPA, alerts.MAX_CKPA
            )
        )
    total = sum(r["ckpa"] for r in readings)
    per_sensor = {}
    for reading in readings:
        bucket = per_sensor.setdefault(reading["sensor"], [0, 0])
        bucket[0] += reading["ckpa"]
        bucket[1] += 1
    return {
        "mean_ckpa": total // len(readings),
        "below": below,
        "above": above,
        "sensor_mean": {k: v[0] // v[1] for k, v in per_sensor.items()},
    }
