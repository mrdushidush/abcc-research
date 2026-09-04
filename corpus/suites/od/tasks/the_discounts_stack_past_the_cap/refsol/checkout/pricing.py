"""Discounts.

Everything is integer cents. `MAX_TOTAL_PCT` is the floor margin finance set;
it is not a suggestion and it is not per-code.
"""

MAX_TOTAL_PCT = 50


def total_pct(discounts):
    return sum(d["pct"] for d in discounts)


def payable(subtotal_cents, discounts):
    """What the customer pays after every discount on the order.

    The percentages ADD and the total is capped at `MAX_TOTAL_PCT`
    (docs/discounts.md). Applying them one after another compounds, which is
    neither what the codes promise nor what the cap was written against.
    """
    pct = min(total_pct(discounts), MAX_TOTAL_PCT)
    return subtotal_cents - (subtotal_cents * pct) // 100
