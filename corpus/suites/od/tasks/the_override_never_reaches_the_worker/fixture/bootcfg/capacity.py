"""The capacity floor.

A worker that can move fewer than a thousand rows in flight cannot keep up with
the queue, and the failure mode is a backlog nobody notices for a day.
"""

MIN_THROUGHPUT = 1000


class ThroughputTooLow(Exception):
    pass


def throughput(config):
    return config["concurrency"] * config["batch_size"]


def check(config):
    value = throughput(config)
    if value < MIN_THROUGHPUT:
        raise ThroughputTooLow(
            "throughput {} is below the floor of {} -- concurrency {}, batch {}".format(
                value, MIN_THROUGHPUT, config["concurrency"], config["batch_size"]
            )
        )
    return value
