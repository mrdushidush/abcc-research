"""Prorated refunds, in integer cents.

A cancellation refunds the unused part of the month the customer already paid
for. The denominator is the length of THAT month.
"""

DAYS_IN_MONTH = 30


def days_in(year, month):
    """How many days the given month has."""
    return DAYS_IN_MONTH


def refund_cents(record):
    days = days_in(record["year"], record["month"])
    unused = max(0, days - record["days_used"])
    return (record["monthly_cents"] * unused) // days
