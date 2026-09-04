"""Per-queue attempt ceilings."""

CEILING = {
    "sync": 8,
    "webhook": 7,
    "email": 3,
}


def ceiling(queue):
    return CEILING.get(queue, 5)
