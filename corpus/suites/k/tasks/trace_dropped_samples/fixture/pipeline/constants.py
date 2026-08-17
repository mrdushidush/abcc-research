"""Wire-format constants for the telemetry pipeline.

These mirror the values the device firmware emits. Changing one here without
checking `docs/firmware_notes.md` is how field data goes missing.
"""

# Quality flags the ingest stage will accept. Anything else is treated as an
# unusable reading and dropped before it can pollute an average.
#
# Firmware rev A emits these lower-case. See docs/firmware_notes.md for what
# rev B does differently.
VALID_FLAGS = frozenset({"ok", "warn"})

# Flags that are accepted but counted separately, so a noisy device shows up in
# the report instead of quietly dragging the mean around.
DEGRADED_FLAGS = frozenset({"warn"})

# Channels the roll-up knows how to interpret. A sample on any other channel is
# dropped with a counted reason rather than silently ignored.
KNOWN_CHANNELS = ("temp_c", "pressure_kpa", "flow_lpm", "vibration_mm_s")

# Physical plausibility bounds, per channel. A reading outside these is a sensor
# fault, not a measurement, and must never reach the statistics stage.
CHANNEL_BOUNDS = {
    "temp_c": (-40.0, 150.0),
    "pressure_kpa": (0.0, 1200.0),
    "flow_lpm": (0.0, 500.0),
    "vibration_mm_s": (0.0, 80.0),
}

# Reason codes used by the drop counters. The report prints these verbatim, so
# they are part of the output contract.
DROP_UNKNOWN_CHANNEL = "unknown_channel"
DROP_BAD_FLAG = "bad_flag"
DROP_OUT_OF_BOUNDS = "out_of_bounds"
DROP_MALFORMED = "malformed"

DROP_REASONS = (
    DROP_UNKNOWN_CHANNEL,
    DROP_BAD_FLAG,
    DROP_OUT_OF_BOUNDS,
    DROP_MALFORMED,
)

# Sample timestamps arrive as integer milliseconds since the run started.
TIMESTAMP_KEY = "t_ms"
VALUE_KEY = "value"
CHANNEL_KEY = "channel"
FLAG_KEY = "flag"
DEVICE_KEY = "device"
