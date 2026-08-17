"""Shape checks for records moving between stages.

These are cheap assertions used by the tests and by `--strict` runs. They are
deliberately NOT run in the hot path: a roll-up that validates every record
against a schema twice per stage spends more time checking than computing.
"""

from . import constants

# The canonical record shape, after normalisation.
RECORD_FIELDS = {
    constants.TIMESTAMP_KEY: int,
    constants.CHANNEL_KEY: str,
    constants.VALUE_KEY: float,
    constants.FLAG_KEY: str,
    constants.DEVICE_KEY: str,
}


class SchemaError(ValueError):
    pass


def check_record(rec):
    """Raise SchemaError unless `rec` is a canonical record."""
    if not isinstance(rec, dict):
        raise SchemaError("record is %s, not dict" % type(rec).__name__)

    for field, want in RECORD_FIELDS.items():
        if field not in rec:
            raise SchemaError("record missing field %r" % field)
        if not isinstance(rec[field], want):
            raise SchemaError(
                "field %r is %s, expected %s"
                % (field, type(rec[field]).__name__, want.__name__)
            )

    if rec[constants.CHANNEL_KEY] != rec[constants.CHANNEL_KEY].lower():
        raise SchemaError("channel %r is not lower-case" % rec[constants.CHANNEL_KEY])

    # The same rule as the channel, and the one that is easy to forget: a flag
    # that reaches this point still carrying rev B's upper-case spelling has
    # skipped normalisation somewhere upstream.
    if rec[constants.FLAG_KEY] != rec[constants.FLAG_KEY].lower():
        raise SchemaError("flag %r is not lower-case" % rec[constants.FLAG_KEY])

    return True


def check_all(records):
    """Check a sequence, returning (ok_count, [error strings])."""
    ok = 0
    errors = []
    for i, rec in enumerate(records):
        try:
            check_record(rec)
            ok += 1
        except SchemaError as exc:
            errors.append("record %d: %s" % (i, exc))
    return ok, errors


def describe():
    return ", ".join(
        "%s:%s" % (name, typ.__name__) for name, typ in sorted(RECORD_FIELDS.items())
    )
