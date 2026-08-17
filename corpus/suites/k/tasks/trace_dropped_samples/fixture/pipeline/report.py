"""Render a summary as text.

The output format is a contract: the verifier parses these lines. Adding a
line is safe; changing an existing line's shape is not.
"""

from . import constants


def render(summary, settings):
    lines = []
    prec = settings.precision

    lines.append("TELEMETRY ROLL-UP")
    lines.append("windows: %d" % len(summary.windows))
    lines.append("samples: %d" % summary.total_samples)

    for channel in settings.report_channels:
        mean = summary.channel_mean(channel)
        bucket = summary.per_channel.get(channel) or {"n": 0, "peak": None}
        if mean is None:
            lines.append("channel %s n=0 mean=n/a peak=n/a" % channel)
            continue
        peak = bucket.get("peak")
        peak_text = "n/a" if peak is None else ("%.*f" % (prec, peak))
        lines.append(
            "channel %s n=%d mean=%.*f peak=%s"
            % (channel, bucket["n"], prec, mean, peak_text)
        )

    return "\n".join(lines)


def render_drops(accepted):
    """Render the drop accounting. Printed by the diagnostic entry point."""
    lines = ["DROPS total=%d" % accepted.total_dropped()]
    for reason in constants.DROP_REASONS:
        lines.append("  %s=%d" % (reason, accepted.drops.get(reason, 0)))
    return "\n".join(lines)
