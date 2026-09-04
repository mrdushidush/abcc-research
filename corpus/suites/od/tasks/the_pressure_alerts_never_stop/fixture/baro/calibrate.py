"""Per-sensor calibration.

Each sensor has a bench offset measured at installation, quoted in hPa because
that is what the bench report gives.
"""

from . import units


def apply(readings, offsets):
    out = []
    for reading in readings:
        offset_hpa = offsets.get(reading["sensor"], 0)
        value = units.to_ckpa(reading["ckpa"]) + units.to_ckpa(offset_hpa)
        out.append({"id": reading["id"], "sensor": reading["sensor"], "ckpa": value})
    return out
