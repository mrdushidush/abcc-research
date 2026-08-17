"""Output sinks. The text report is one of several; none of them may mutate
the summary they are handed.
"""

import json

from . import constants


class Sink:
    name = "base"

    def emit(self, summary, settings):
        raise NotImplementedError


class JsonSink(Sink):
    """Machine-readable output, one JSON object per run."""

    name = "json"

    def emit(self, summary, settings):
        payload = {
            "windows": len(summary.windows),
            "samples": summary.total_samples,
            "channels": {},
        }
        for channel in settings.report_channels:
            bucket = summary.per_channel.get(channel)
            mean = summary.channel_mean(channel)
            payload["channels"][channel] = {
                "n": (bucket or {}).get("n", 0),
                "mean": None if mean is None else round(mean, settings.precision),
                "peak": (bucket or {}).get("peak"),
            }
        return json.dumps(payload, sort_keys=True)


class CsvSink(Sink):
    """One row per window. Header is fixed and part of the contract."""

    name = "csv"

    HEADER = "channel,start_ms,n,mean,peak,degraded"

    def emit(self, summary, settings):
        rows = [self.HEADER]
        for stat in summary.windows:
            peak = "" if stat.peak is None else ("%.*f" % (settings.precision, stat.peak))
            rows.append(
                "%s,%d,%d,%.*f,%s,%d"
                % (
                    stat.channel,
                    stat.start_ms,
                    stat.n,
                    settings.precision,
                    stat.mean,
                    peak,
                    stat.degraded,
                )
            )
        return "\n".join(rows)


class NullSink(Sink):
    """Discards everything. Used by the timing harness."""

    name = "null"

    def emit(self, summary, settings):
        return ""


REGISTRY = {sink.name: sink for sink in (JsonSink, CsvSink, NullSink)}


def get(name):
    if name not in REGISTRY:
        raise KeyError(
            "unknown sink %r; known: %s" % (name, ", ".join(sorted(REGISTRY)))
        )
    return REGISTRY[name]()
