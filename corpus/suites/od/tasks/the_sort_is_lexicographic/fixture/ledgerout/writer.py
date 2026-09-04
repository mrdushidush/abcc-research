"""Writing the ledger file."""

from . import ordering


def emit(records):
    """The records, in the order they will be written."""
    return [r["id"] for r in ordering.ordered(records)]


def running_balance(records):
    balance, trail = 0, []
    for record in ordering.ordered(records):
        balance += record["amount_cents"]
        trail.append(balance)
    return trail
