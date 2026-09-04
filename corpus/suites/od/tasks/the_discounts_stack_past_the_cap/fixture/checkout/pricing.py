"""Discounts.

Everything is integer cents. `MAX_TOTAL_PCT` is the floor margin finance set;
it is not a suggestion and it is not per-code.
"""

MAX_TOTAL_PCT = 50


def total_pct(discounts):
    return sum(d["pct"] for d in discounts)


def payable(subtotal_cents, discounts):
    """What the customer pays after every discount on the order."""
    remaining = subtotal_cents
    for discount in discounts:
        remaining = remaining - (remaining * discount["pct"]) // 100
    return remaining
