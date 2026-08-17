"""Telemetry roll-up pipeline.

Stage order, and the shape each stage hands on:

    ingest.accept      raw dicts        -> Accepted (samples + drop counters)
    calibration.apply  Accepted         -> Accepted (values corrected in place)
    windowing.split    Accepted         -> [Window]
    stats.summarise    [Window]         -> Summary
    report.render      Summary          -> str

`normalize` is a helper used by ingest, not a stage of its own. Everything it
exposes is idempotent, so calling it twice on a record is harmless.
"""

__all__ = [
    "calibration",
    "config",
    "constants",
    "ingest",
    "normalize",
    "report",
    "stats",
    "transport",
    "validate",
    "windowing",
]

VERSION = "2.4.0"
