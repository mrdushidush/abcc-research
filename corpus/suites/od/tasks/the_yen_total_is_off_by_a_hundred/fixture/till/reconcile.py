"""Reconciling our arithmetic against the payment provider's.

The provider settles in minor units and tells us what it took. If our line
totals do not add up to that, one of the two is wrong about what the customer
paid and we do not get to guess which.
"""

from . import lines


class TotalMismatch(Exception):
    pass


def check(orders):
    mismatches = []
    for order in orders:
        ours = lines.order_total(order)
        theirs = order["provider_total_minor"]
        if ours != theirs:
            mismatches.append((order["id"], ours, theirs))
    if mismatches:
        first = mismatches[0]
        raise TotalMismatch(
            "{} orders disagree with the provider; first is {}: we say {}, they say "
            "{}".format(len(mismatches), first[0], first[1], first[2])
        )
    return len(orders)
