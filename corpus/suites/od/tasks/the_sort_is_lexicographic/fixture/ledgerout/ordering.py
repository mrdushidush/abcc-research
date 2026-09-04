"""The order records are written in.

The downstream reader replays the file top to bottom and applies each record to
a running balance, so the file's order IS the ledger's order.
"""


def sort_key(record):
    """The key records are ordered by."""
    return str(record["seq"])


def ordered(records):
    return sorted(records, key=sort_key)
