"""Visible tests.

⚠ Every range here is a plain working week with no holiday in it, so the
holiday lookup never changes an answer. `TABLE` is asserted as a table — its
contents are right — and `for_year` is never asked for a year whose answer a
test knows.
"""

import datetime

from worksched import businessdays, closures, holidays, invoices, sla


def d(text):
    return datetime.date.fromisoformat(text)


def test_table_has_a_row_per_calendar_year():
    assert set(holidays.TABLE) == {2025, 2026, 2027}
    assert "2026-04-03" in holidays.TABLE[2026]


def test_weekends_are_not_business_days():
    assert businessdays.is_business_day(d("2026-06-13")) is False   # Saturday
    assert businessdays.is_business_day(d("2026-06-14")) is False   # Sunday
    assert businessdays.is_business_day(d("2026-06-15")) is True    # Monday


def test_add_business_days_skips_the_weekend():
    assert businessdays.add_business_days(d("2026-06-12"), 1) == d("2026-06-15")
    assert businessdays.add_business_days(d("2026-06-15"), 3) == d("2026-06-18")


def test_sla_due_is_business_days_after_opening():
    assert sla.due({"id": "t", "opened": "2026-06-15", "sla_days": 2}) == d("2026-06-17")


def test_invoice_due_uses_the_same_arithmetic():
    assert invoices.due({"id": "i", "issued": "2026-06-15", "terms_days": 2}) == d("2026-06-17")


def test_closures_reads_the_feed():
    feed = closures.Closures(["2026-04-03"])
    assert feed.closed(d("2026-04-03")) is True
    assert feed.closed(d("2026-04-06")) is False
