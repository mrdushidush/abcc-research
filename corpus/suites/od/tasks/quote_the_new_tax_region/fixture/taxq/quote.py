"""Quoting one order.

Rounds half up in integer cents; there is no float in the money path.
"""

from . import exemptions, rates


def tax_cents(order):
    if exemptions.exempt(order["region"], order["category"]):
        return 0
    gross = order["amount_cents"] * rates.basis_points(order["region"])
    return (gross + 5000) // 10000
