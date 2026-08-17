"""Plausibility checks. A reading outside these bounds is a sensor fault."""

from . import constants


def in_bounds(channel, value):
    """True when `value` is physically plausible for `channel`.

    An unknown channel has no bounds to check against, so it is reported as
    out of bounds rather than waved through — an unknown channel should have
    been dropped by the caller before reaching here.
    """
    bounds = constants.CHANNEL_BOUNDS.get(channel)
    if bounds is None:
        return False
    low, high = bounds
    return low <= value <= high


def clamp(channel, value):
    """Clamp `value` into the channel's bounds. Used by the calibration stage,
    which may push a reading marginally outside after applying an offset."""
    bounds = constants.CHANNEL_BOUNDS.get(channel)
    if bounds is None:
        return value
    low, high = bounds
    return max(low, min(high, value))


def describe_bounds(channel):
    bounds = constants.CHANNEL_BOUNDS.get(channel)
    if bounds is None:
        return "unbounded"
    return "%.1f..%.1f" % bounds
