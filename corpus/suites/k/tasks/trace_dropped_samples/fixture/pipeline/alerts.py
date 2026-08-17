"""Threshold alerting over summarised windows.

Alerts are evaluated after the roll-up, never during ingest: an alert on a raw
reading fires on sensor noise, and an alert on a window mean fires on the thing
an operator actually cares about.

Severity ladder, lowest first: `info`, `notice`, `warning`, `critical`. A window
raises at most one alert per channel — the highest one whose condition holds.
"""

from . import constants

# channel -> ordered list of (severity, comparison, threshold). Evaluated top
# down; the FIRST match wins, so these must stay ordered most severe first.
THRESHOLDS = {
    "temp_c": [
        ("critical", "gt", 120.0),
        ("warning", "gt", 90.0),
        ("notice", "gt", 60.0),
        ("notice", "lt", -20.0),
    ],
    "pressure_kpa": [
        ("critical", "gt", 1000.0),
        ("warning", "gt", 800.0),
        ("notice", "lt", 50.0),
    ],
    "flow_lpm": [
        ("critical", "lt", 1.0),
        ("warning", "lt", 5.0),
        ("notice", "gt", 400.0),
    ],
    "vibration_mm_s": [
        ("critical", "gt", 60.0),
        ("warning", "gt", 35.0),
        ("notice", "gt", 20.0),
    ],
}

SEVERITY_ORDER = ("info", "notice", "warning", "critical")


class Alert:
    def __init__(self, channel, start_ms, severity, reason, value):
        self.channel = channel
        self.start_ms = start_ms
        self.severity = severity
        self.reason = reason
        self.value = value

    def __repr__(self):
        return "Alert(%s@%d %s %s value=%.3f)" % (
            self.channel,
            self.start_ms,
            self.severity,
            self.reason,
            self.value,
        )


def _holds(comparison, value, threshold):
    if comparison == "gt":
        return value > threshold
    if comparison == "lt":
        return value < threshold
    raise ValueError("unknown comparison %r" % (comparison,))


def evaluate_window(stat):
    """Return the single highest-severity Alert for a window stat, or None.

    A window with no samples raises nothing. That is deliberate: an empty
    window means the roll-up has no opinion, and firing a `flow_lpm` low-flow
    critical on an absence of data is how a monitoring system loses its
    audience.
    """
    if stat.n == 0:
        return None

    rules = THRESHOLDS.get(stat.channel)
    if not rules:
        return None

    for severity, comparison, threshold in rules:
        if _holds(comparison, stat.mean, threshold):
            reason = "%s %s %.3f" % (stat.channel, comparison, threshold)
            return Alert(stat.channel, stat.start_ms, severity, reason, stat.mean)
    return None


def evaluate(summary):
    """Evaluate every window in a summary. Returns alerts in window order."""
    out = []
    for stat in summary.windows:
        alert = evaluate_window(stat)
        if alert is not None:
            out.append(alert)
    return out


def worst(alerts):
    """The highest severity present, or None."""
    seen = None
    for alert in alerts:
        if seen is None or SEVERITY_ORDER.index(alert.severity) > SEVERITY_ORDER.index(seen):
            seen = alert.severity
    return seen


def summarise_alerts(alerts):
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for alert in alerts:
        counts[alert.severity] = counts.get(alert.severity, 0) + 1
    return counts
