"""Billing.

Stage order:

    catalog          SKU -> Entry (unit prices, 4 dp)
    discounts        customer/category/qty -> discount rate
    tax              region -> tax rate
    pricing          order items + catalogue + tax rate -> [Line]
    invoice          [Line] -> Invoice (lines + total)
    receipt          Invoice -> text the customer reads
    ledger           Invoice -> integer-cent entries we book
    audit            [Invoice] -> findings, no corrections

`money` is not a stage. It is the only module allowed to round, and every
amount that crosses a stage boundary should have been through it. See
docs/money.md.
"""

__all__ = [
    "audit",
    "catalog",
    "discounts",
    "invoice",
    "ledger",
    "money",
    "pricing",
    "receipt",
    "tax",
    "validate",
]

VERSION = "3.1.0"
