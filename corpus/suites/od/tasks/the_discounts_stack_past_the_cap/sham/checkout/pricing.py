"""Discounts.

Everything is integer cents. `MAX_TOTAL_PCT` is the floor margin finance set;
it is not a suggestion and it is not per-code.
"""

MAX_TOTAL_PCT = 50


def total_pct(discounts):
    return sum(d["pct"] for d in discounts)


def payable(subtotal_cents, discounts):
    """What the customer pays after every discount on the order.

    The percentages add: 20% and 10% is 30% off, not 28%.
    """
    pct = total_pct(discounts)
    return subtotal_cents - (subtotal_cents * pct) // 100
