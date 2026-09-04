"""Visible tests.

⚠ Every amount here is in a two-decimal currency, so `to_minor` is never asked
about the two rows of `MINOR_UNITS` that are not 2. The table itself is
asserted and is correct — nothing reads it.
"""

from till import lines, money, reconcile


def order(ident, currency, provider, amounts):
    return {
        "id": ident,
        "currency": currency,
        "provider_total_minor": provider,
        "lines": [{"sku": str(i), "amount": a} for i, a in enumerate(amounts)],
    }


def test_minor_units_table_is_not_two_everywhere():
    assert money.minor_units("USD") == 2
    assert money.minor_units("JPY") == 0
    assert money.minor_units("KWD") == 3


def test_to_minor_on_a_two_decimal_currency():
    assert money.to_minor("12.50", "USD") == 1250
    assert money.to_minor("0.01", "EUR") == 1


def test_line_total_is_minor_units():
    assert lines.line_total({"sku": "a", "amount": "19.99"}, "EUR") == 1999


def test_order_total_sums_the_lines():
    assert lines.order_total(order("o", "USD", 4250, ["12.50", "30.00"])) == 4250


def test_reconcile_accepts_agreeing_totals():
    assert reconcile.check([order("o", "USD", 4250, ["12.50", "30.00"])]) == 1
