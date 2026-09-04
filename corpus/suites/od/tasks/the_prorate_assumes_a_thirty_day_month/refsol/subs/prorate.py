"""Prorated refunds, in integer cents.

A cancellation refunds the unused part of the month the customer already paid
for. The denominator is the length of THAT month.
"""

import calendar

DAYS_IN_MONTH = 30


def days_in(year, month):
    """How many days the given month has.

    The real length of the real month, leap years included -- the customer paid
    for a month and not for thirty days (docs/prorate.md).
    """
    return calendar.monthrange(year, month)[1]


def refund_cents(record):
    days = days_in(record["year"], record["month"])
    unused = max(0, days - record["days_used"])
    return (record["monthly_cents"] * unused) // days
