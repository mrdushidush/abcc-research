"""Ingest: turn raw device records into accepted samples, with drop accounting.

Every rejection is counted against a reason code from `constants.DROP_REASONS`
so the report can say what was thrown away and why. A silent drop here is the
worst failure mode this pipeline has: the numbers downstream stay plausible.
"""

from . import constants, normalize, validate


class Accepted:
    """Accepted samples plus the drop counters that explain the ones missing."""

    def __init__(self):
        self.samples = []
        self.drops = {reason: 0 for reason in constants.DROP_REASONS}
        self.degraded = 0

    def keep(self, rec):
        self.samples.append(rec)
        if rec[constants.FLAG_KEY] in constants.DEGRADED_FLAGS:
            self.degraded += 1

    def drop(self, reason):
        self.drops[reason] = self.drops.get(reason, 0) + 1

    def total_dropped(self):
        return sum(self.drops.values())

    def __len__(self):
        return len(self.samples)


def accept(raw_records, settings):
    """Filter `raw_records` down to the samples the roll-up will use.

    Order of checks is deliberate: cheapest and most decisive first, so a
    malformed record never reaches a bounds check that would raise on it.
    """
    out = Accepted()

    for raw in raw_records:
        rec = normalize.canonical_record(raw)

        if constants.TIMESTAMP_KEY not in rec or constants.VALUE_KEY not in rec:
            out.drop(constants.DROP_MALFORMED)
            continue

        try:
            rec[constants.TIMESTAMP_KEY] = int(rec[constants.TIMESTAMP_KEY])
            rec[constants.VALUE_KEY] = float(rec[constants.VALUE_KEY])
        except (TypeError, ValueError):
            out.drop(constants.DROP_MALFORMED)
            continue

        channel = normalize.canonical_channel(rec.get(constants.CHANNEL_KEY))
        rec[constants.CHANNEL_KEY] = channel
        if channel not in constants.KNOWN_CHANNELS:
            out.drop(constants.DROP_UNKNOWN_CHANNEL)
            continue

        # Quality gate. VALID_FLAGS is written in rev A's lower-case spelling.
        flag = rec.get(constants.FLAG_KEY)
        if flag not in constants.VALID_FLAGS:
            out.drop(constants.DROP_BAD_FLAG)
            continue
        rec[constants.FLAG_KEY] = flag

        rec[constants.DEVICE_KEY] = str(rec.get(constants.DEVICE_KEY, "unknown"))

        if not validate.in_bounds(channel, rec[constants.VALUE_KEY]):
            out.drop(constants.DROP_OUT_OF_BOUNDS)
            continue

        out.keep(rec)

    return out
