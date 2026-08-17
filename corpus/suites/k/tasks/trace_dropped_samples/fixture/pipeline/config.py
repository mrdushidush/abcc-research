"""Run settings.

Defaults live here. `load()` is the only supported way to obtain them, so a
future override layer has one place to hook into.
"""

# Window length for the roll-up, in milliseconds. The device emits at 50 Hz,
# so a 10-second window is 500 samples per channel when nothing is dropped.
WINDOW_MS = 10_000

# Channels the report covers, in the order it prints them.
REPORT_CHANNELS = ("temp_c", "pressure_kpa", "flow_lpm", "vibration_mm_s")

# Round every printed figure to this many decimal places. The verifier and the
# report agree on this, so changing it changes the output contract.
PRECISION = 3

# When true, a window with no usable samples is an error rather than a hole.
# It is true because a silent hole in a roll-up is indistinguishable from a
# quiet period, and the two mean very different things to an operator.
STRICT_EMPTY_WINDOWS = True


class Settings:
    def __init__(self, **overrides):
        self.window_ms = overrides.get("window_ms", WINDOW_MS)
        self.report_channels = tuple(overrides.get("report_channels", REPORT_CHANNELS))
        self.precision = overrides.get("precision", PRECISION)
        self.strict_empty_windows = overrides.get(
            "strict_empty_windows", STRICT_EMPTY_WINDOWS
        )

    def __repr__(self):
        return "Settings(window_ms=%r, precision=%r, strict_empty_windows=%r)" % (
            self.window_ms,
            self.precision,
            self.strict_empty_windows,
        )


def load(**overrides):
    """Build the settings for a run."""
    return Settings(**overrides)
