"""Grouping orders."""


def by_region(orders):
    out = {}
    for order in orders:
        out.setdefault(order["region"], []).append(order["amount_cents"])
    return out
