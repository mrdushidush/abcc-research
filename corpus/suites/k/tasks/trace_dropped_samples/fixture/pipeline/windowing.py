"""Split accepted samples into fixed-length windows, per channel.

A window is identified by its start time in milliseconds, so windows are
comparable across runs and across devices without carrying a wall clock.
"""

from . import constants


class Window:
    def __init__(self, channel, start_ms, end_ms):
        self.channel = channel
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.values = []
        self.devices = set()
        self.degraded = 0

    def add(self, rec):
        self.values.append(rec[constants.VALUE_KEY])
        self.devices.add(rec[constants.DEVICE_KEY])
        if rec[constants.FLAG_KEY] in constants.DEGRADED_FLAGS:
            self.degraded += 1

    def __len__(self):
        return len(self.values)

    def __repr__(self):
        return "Window(%s, %d..%d, n=%d)" % (
            self.channel,
            self.start_ms,
            self.end_ms,
            len(self.values),
        )


def window_start(t_ms, window_ms):
    """Floor `t_ms` to the start of its window."""
    return (t_ms // window_ms) * window_ms


def split(accepted, settings):
    """Group accepted samples into windows, keyed by (channel, start_ms).

    Returns a list of Window ordered by channel (in report order) then by
    start time, so the report and the verifier see a stable ordering.

    Every window between the first and last observed start time is emitted for
    each reported channel, INCLUDING windows that received no samples. A hole
    that is not emitted is a hole nobody can notice.
    """
    window_ms = settings.window_ms
    buckets = {}
    starts = set()

    for rec in accepted.samples:
        channel = rec[constants.CHANNEL_KEY]
        start = window_start(rec[constants.TIMESTAMP_KEY], window_ms)
        starts.add(start)
        key = (channel, start)
        if key not in buckets:
            buckets[key] = Window(channel, start, start + window_ms)
        buckets[key].add(rec)

    if not starts:
        return []

    first, last = min(starts), max(starts)
    all_starts = list(range(first, last + window_ms, window_ms))

    out = []
    for channel in settings.report_channels:
        for start in all_starts:
            key = (channel, start)
            if key in buckets:
                out.append(buckets[key])
            else:
                out.append(Window(channel, start, start + window_ms))
    return out
