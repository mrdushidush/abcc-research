"""Money handling.

Every monetary value in this service is a float in major currency units
(21.50 means twenty-one pounds fifty). That is a decision we regret and have
not yet paid to undo — see docs/money.md — so the mitigation is that ALL
rounding goes through this module and nowhere else.

`to_cents` is the only correct way to reduce a computed amount to something a
customer can be charged. Python's built-in `round` is banker's rounding, which
rounds 2.675 to 2.67, and finance expects 2.68.
"""

import math

CENTS = 100

# Anything below this is treated as float noise rather than money. Used by the
# reconciliation checks, never by the rounding itself.
EPSILON = 1e-9


def to_cents(amount):
    """Round `amount` to whole cents, half away from zero, and return an int.

    Half-away-from-zero, not banker's rounding: an invoice that rounds 2.675
    down to 2.67 gets queried by the customer, and we have lost that argument
    before.
    """
    if amount >= 0:
        return int(math.floor(amount * CENTS + 0.5))
    return -int(math.floor(-amount * CENTS + 0.5))


def from_cents(cents):
    """Turn whole cents back into major units."""
    return cents / CENTS


def quantize(amount):
    """Round `amount` to a chargeable amount in major units.

    This is the function every stage should be calling before it hands an
    amount to another stage. Rounding once at the very end of a calculation is
    NOT equivalent: the customer sees the per-line amounts, and per-line
    amounts that do not sum to the total is the single most common billing
    complaint we get.
    """
    return from_cents(to_cents(amount))


def format_amount(amount, symbol="£"):
    """Render an amount for display. Assumes it is already quantized."""
    return "%s%.2f" % (symbol, amount)


def sum_amounts(amounts):
    """Sum a sequence of already-quantized amounts without reintroducing drift.

    Sums in integer cents rather than floats, so 0.1 + 0.2 does not become
    0.30000000000000004 and a total does not disagree with its own lines.
    """
    total_cents = 0
    for amount in amounts:
        total_cents += to_cents(amount)
    return from_cents(total_cents)


def is_whole_cents(amount):
    """True when `amount` is exactly representable in whole cents."""
    return abs(amount * CENTS - round(amount * CENTS)) < EPSILON
