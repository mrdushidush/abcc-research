"""The JSON body the customer portal fetches."""

import json

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
    return json.dumps(
        {"lines": transactions, "total_cents": total(transactions)}, sort_keys=True
    )
