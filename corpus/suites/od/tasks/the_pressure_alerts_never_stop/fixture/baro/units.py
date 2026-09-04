"""Units.

Sensors report in hectopascals. Everything downstream of `ingest` works in
**centi-kilopascals** — kPa scaled by 100 — because the alert bounds are quoted
to two decimal places and there is no float anywhere in this pipeline.

    1 hPa = 0.1 kPa = 10 cKPa
"""


def to_ckpa(hpa):
    """Convert a raw hectopascal reading to centi-kilopascals."""
    return int(hpa) * 10
