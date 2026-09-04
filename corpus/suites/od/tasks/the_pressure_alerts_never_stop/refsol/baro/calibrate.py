"""Per-sensor calibration.

Each sensor has a bench offset measured at installation, quoted in hPa because
that is what the bench report gives.
"""

from . import units


def apply(readings, offsets):
    out = []
    for reading in readings:
        offset_hpa = offsets.get(reading["sensor"], 0)
        # `reading["ckpa"]` is already in cKPa -- `ingest` is the unit boundary
        # (docs/units.md). Only the bench offset still needs converting.
        value = reading["ckpa"] + units.to_ckpa(offset_hpa)
        out.append({"id": reading["id"], "sensor": reading["sensor"], "ckpa": value})
    return out
