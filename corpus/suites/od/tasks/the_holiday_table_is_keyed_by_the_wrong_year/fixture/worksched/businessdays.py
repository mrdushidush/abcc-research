"""Business-day arithmetic.

A business day is a weekday that is not a company holiday.
"""

import datetime

from . import holidays


def parse(text):
    return datetime.date.fromisoformat(text)


def is_business_day(day):
    if day.weekday() >= 5:
        return False
    return not holidays.is_holiday(day)


def add_business_days(start, count):
    """The date `count` business days after `start`."""
    day = start
    remaining = count
    while remaining > 0:
        day = day + datetime.timedelta(days=1)
        if is_business_day(day):
            remaining -= 1
    return day
