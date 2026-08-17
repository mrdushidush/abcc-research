"""Retention policy for windowed results.

The roll-up keeps full-resolution windows for a short period, then downsamples
to hourly aggregates, then drops. Nothing here touches ingest; it operates on
windows that have already been summarised.
"""

FULL_RESOLUTION_MS = 24 * 60 * 60 * 1000       # 24h of 10s windows
HOURLY_RESOLUTION_MS = 30 * 24 * 60 * 60 * 1000  # 30d of hourly aggregates

HOUR_MS = 60 * 60 * 1000


class Bucket:
    def __init__(self, channel, start_ms):
        self.channel = channel
        self.start_ms = start_ms
        self.n = 0
        self.total = 0.0
        self.peak = None

    def add(self, stat):
        self.n += stat.n
        self.total += stat.mean * stat.n
        if stat.peak is not None and (self.peak is None or stat.peak > self.peak):
            self.peak = stat.peak

    @property
    def mean(self):
        if self.n == 0:
            return None
        return self.total / self.n


def classify(stat, now_ms):
    """Which retention tier a window belongs to, given the current time."""
    age = now_ms - stat.start_ms
    if age <= FULL_RESOLUTION_MS:
        return "full"
    if age <= HOURLY_RESOLUTION_MS:
        return "hourly"
    return "drop"


def downsample_to_hourly(stats):
    """Collapse window stats into hourly buckets, per channel.

    Windows with no samples contribute nothing — they are not zeros. Averaging
    a hole in as a zero is the same class of mistake as reporting an empty
    window's mean as 0.0, and it produces the same kind of quietly wrong graph.
    """
    buckets = {}
    for stat in stats:
        if stat.n == 0:
            continue
        hour_start = (stat.start_ms // HOUR_MS) * HOUR_MS
        key = (stat.channel, hour_start)
        if key not in buckets:
            buckets[key] = Bucket(stat.channel, hour_start)
        buckets[key].add(stat)
    return [buckets[k] for k in sorted(buckets)]


def apply_policy(stats, now_ms):
    """Split window stats into (kept_full, downsampled_hourly, dropped_count)."""
    full, to_downsample, dropped = [], [], 0
    for stat in stats:
        tier = classify(stat, now_ms)
        if tier == "full":
            full.append(stat)
        elif tier == "hourly":
            to_downsample.append(stat)
        else:
            dropped += 1
    return full, downsample_to_hourly(to_downsample), dropped
