"""The transaction kinds.

`partial_refund` arrived with the returns feature. It is a refund: it moves
money back to the customer, it just does not move all of it.
"""

CHARGE = "charge"
REFUND = "refund"
PARTIAL_REFUND = "partial_refund"

ALL = (CHARGE, REFUND, PARTIAL_REFUND)

# Every kind that takes money away from the total.
REFUND_KINDS = (REFUND, PARTIAL_REFUND)
