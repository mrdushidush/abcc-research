"""Visible tests.

⚠ Every month here is a thirty-day month — April, June, September — so the
denominator is thirty in every case the suite covers and nothing distinguishes
a constant from a lookup.
"""

from subs import prorate


def record(year, month, monthly, used):
    return {"id": "x", "plan": "p", "year": year, "month": month,
            "monthly_cents": monthly, "days_used": used}


def test_a_thirty_day_month_has_thirty_days():
    assert prorate.days_in(2026, 4) == 30
    assert prorate.days_in(2026, 6) == 30
    assert prorate.days_in(2026, 9) == 30


def test_half_a_thirty_day_month():
    assert prorate.refund_cents(record(2026, 4, 3000, 15)) == 1500


def test_cancelling_on_day_one_refunds_almost_everything():
    assert prorate.refund_cents(record(2026, 6, 3000, 1)) == 2900


def test_using_the_whole_month_refunds_nothing():
    assert prorate.refund_cents(record(2026, 9, 3000, 30)) == 0


def test_overrunning_the_month_refunds_nothing():
    assert prorate.refund_cents(record(2026, 9, 3000, 45)) == 0
