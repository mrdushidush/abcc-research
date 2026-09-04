"""The one-line summary the support console shows."""

from . import kinds


def total(transactions):
    running = 0
    for txn in transactions:
        if txn["kind"] in kinds.REFUND_KINDS:
            running -= txn["amount_cents"]
        else:
            running += txn["amount_cents"]
    return running


def render(transactions):
    return "{} transactions, {} cents".format(len(transactions), total(transactions))
