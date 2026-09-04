"""Range alerts.

Bounds are the instrument's operating range, in centi-kilopascals:
90.00 kPa to 110.00 kPa. A reading outside it is a fault. They are a property of
the hardware and not a tuning knob.
"""

MIN_CKPA = 9000
MAX_CKPA = 11000


def out_of_range(readings):
    below = [r["id"] for r in readings if r["ckpa"] < MIN_CKPA]
    above = [r["id"] for r in readings if r["ckpa"] > MAX_CKPA]
    return below, above
