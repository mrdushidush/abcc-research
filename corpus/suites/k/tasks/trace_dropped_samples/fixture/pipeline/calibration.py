"""Per-device calibration offsets.

Each device carries a small linear correction, `value * gain + offset`, applied
after ingest and before windowing. Devices with no entry use the identity
correction rather than being dropped — an uncalibrated device still measures
something, and dropping it would hide a whole unit from the roll-up.
"""

from . import constants, validate

# device id -> (gain, offset). Derived from the last bench calibration.
CALIBRATION_TABLE = {
    "dev-a1": (1.0, 0.0),
    "dev-a2": (1.0, -0.25),
    "dev-b1": (1.0, 0.0),
    "dev-b2": (1.0, 0.5),
}

IDENTITY = (1.0, 0.0)


def load_table(settings):
    """Return the calibration table for this run."""
    return dict(CALIBRATION_TABLE)


def correction_for(device, table):
    return table.get(device, IDENTITY)


def apply(accepted, table):
    """Apply per-device calibration in place, clamping into channel bounds.

    Returns the same `Accepted` object so the drop counters survive.
    """
    for rec in accepted.samples:
        gain, offset = correction_for(rec[constants.DEVICE_KEY], table)
        corrected = rec[constants.VALUE_KEY] * gain + offset
        rec[constants.VALUE_KEY] = validate.clamp(rec[constants.CHANNEL_KEY], corrected)
    return accepted
