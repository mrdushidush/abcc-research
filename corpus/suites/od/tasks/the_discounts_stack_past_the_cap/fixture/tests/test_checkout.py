"""Visible tests.

⚠ Every order here has ONE discount, so compounding never occurs and the total
never approaches the cap. `MAX_TOTAL_PCT` and `total_pct` are asserted
directly.
"""

from checkout import pricing


def discounts(*pcts):
    return [{"code": "C{}".format(i), "pct": p} for i, p in enumerate(pcts)]


def test_cap_is_the_floor_margin():
    assert pricing.MAX_TOTAL_PCT == 50


def test_total_pct_adds_the_codes():
    assert pricing.total_pct(discounts(20, 10)) == 30
    assert pricing.total_pct(discounts()) == 0


def test_one_discount_comes_off_the_subtotal():
    assert pricing.payable(10000, discounts(20)) == 8000
    assert pricing.payable(5000, discounts(15)) == 4250


def test_no_discount_pays_the_subtotal():
    assert pricing.payable(10000, discounts()) == 10000


def test_a_single_code_at_the_cap():
    assert pricing.payable(10000, discounts(50)) == 5000
