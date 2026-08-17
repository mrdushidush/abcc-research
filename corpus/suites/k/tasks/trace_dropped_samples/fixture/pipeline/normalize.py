"""Normalisation of raw device records into the pipeline's internal shape.

Firmware revisions disagree about casing and about a couple of field names.
This module is the single place that reconciles them, so that every stage
downstream can assume one canonical shape:

    {"t_ms": int, "channel": str, "value": float, "flag": str, "device": str}

with `channel` and `flag` lower-case.
"""

from . import constants

# Rev B renamed two fields. Rev C (unreleased) is expected to rename none.
FIELD_ALIASES = {
    "ts_ms": constants.TIMESTAMP_KEY,
    "chan": constants.CHANNEL_KEY,
    "val": constants.VALUE_KEY,
    "quality": constants.FLAG_KEY,
    "dev_id": constants.DEVICE_KEY,
}


def canonical_record(raw):
    """Return `raw` with aliased field names resolved. Does not touch values."""
    out = {}
    for key, value in raw.items():
        out[FIELD_ALIASES.get(key, key)] = value
    return out


def canonical_flag(flag):
    """Lower-case and strip a quality flag.

    Rev B firmware emits upper-case flags (`OK`, `WARN`). Rev A emits them
    lower-case. `constants.VALID_FLAGS` is written in rev A's casing, so a
    flag MUST pass through here before it is compared against that set.
    """
    if flag is None:
        return ""
    return str(flag).strip().lower()


def canonical_channel(channel):
    """Lower-case a channel name and map the one legacy spelling."""
    if channel is None:
        return ""
    name = str(channel).strip().lower()
    # Rev A called this `vib_mm_s`; the roll-up has always used the long form.
    if name == "vib_mm_s":
        return "vibration_mm_s"
    return name


def normalize(raw):
    """Full normalisation: field names, then channel, then flag.

    Returns None when the record is too malformed to be worth carrying.
    """
    rec = canonical_record(raw)

    if constants.TIMESTAMP_KEY not in rec or constants.VALUE_KEY not in rec:
        return None

    try:
        rec[constants.TIMESTAMP_KEY] = int(rec[constants.TIMESTAMP_KEY])
        rec[constants.VALUE_KEY] = float(rec[constants.VALUE_KEY])
    except (TypeError, ValueError):
        return None

    rec[constants.CHANNEL_KEY] = canonical_channel(rec.get(constants.CHANNEL_KEY))
    rec[constants.FLAG_KEY] = canonical_flag(rec.get(constants.FLAG_KEY))
    rec[constants.DEVICE_KEY] = str(rec.get(constants.DEVICE_KEY, "unknown"))
    return rec


def normalize_all(records):
    """Normalise a sequence, dropping records that cannot be canonicalised."""
    out = []
    for raw in records:
        rec = normalize(raw)
        if rec is not None:
            out.append(rec)
    return out
