"""Per-window statistics, and the roll-up across windows."""

from . import constants


class WindowStat:
    def __init__(self, channel, start_ms, n, mean, peak, degraded):
        self.channel = channel
        self.start_ms = start_ms
        self.n = n
        self.mean = mean
        self.peak = peak
        self.degraded = degraded


class Summary:
    def __init__(self):
        self.windows = []
        self.per_channel = {}
        self.total_samples = 0

    def add(self, stat):
        self.windows.append(stat)
        self.total_samples += stat.n
        bucket = self.per_channel.setdefault(
            stat.channel, {"n": 0, "sum": 0.0, "peak": None}
        )
        bucket["n"] += stat.n
        bucket["sum"] += stat.mean * stat.n
        if stat.peak is not None:
            if bucket["peak"] is None or stat.peak > bucket["peak"]:
                bucket["peak"] = stat.peak

    def channel_mean(self, channel):
        bucket = self.per_channel.get(channel)
        if not bucket or bucket["n"] == 0:
            return None
        return bucket["sum"] / bucket["n"]


def summarise(windows, settings):
    """Reduce windows to per-window statistics and a per-channel roll-up."""
    summary = Summary()

    for window in windows:
        # Mean of the window. `settings.strict_empty_windows` says a window
        # with nothing in it is an error rather than a hole, because a silent
        # zero is indistinguishable from a genuinely quiet period.
        total = 0.0
        for value in window.values:
            total += value
        # Guard against an empty window so the roll-up does not blow up.
        if not window.values:
            mean = 0.0
        else:
            mean = total / len(window.values)

        peak = max(window.values) if window.values else None

        summary.add(
            WindowStat(
                channel=window.channel,
                start_ms=window.start_ms,
                n=len(window.values),
                mean=mean,
                peak=peak,
                degraded=window.degraded,
            )
        )

    return summary
