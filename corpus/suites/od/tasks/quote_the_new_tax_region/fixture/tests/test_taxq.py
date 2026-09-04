"""Visible tests.

⚠ Every region named here has been live for years, so no test asks a registry
about a region that was added recently. Each registry's default-on-miss is
asserted with a region that does not exist at all, which is the behaviour and
not the bug.
"""

from taxq import exemptions, filing, labels, quote, rates, regions


def order(region, category="hardware", amount=10000):
    return {"id": "o", "region": region, "category": category, "amount_cents": amount}


def test_supported_lists_the_open_markets():
    assert regions.supported("US-CA") is True
    assert regions.supported("ZZ") is False


def test_rates_default_to_zero_for_an_unknown_region():
    assert rates.basis_points("UK") == 2000
    assert rates.basis_points("ZZ") == 0


def test_labels_default_to_empty():
    assert labels.label("EU-DE") == "USt."
    assert labels.label("ZZ") == ""


def test_filing_period_defaults_to_none():
    assert filing.period("EU-DE") == "monthly"
    assert filing.period("ZZ") is None


def test_exemptions_default_to_nothing():
    assert exemptions.exempt("UK", "books") is True
    assert exemptions.exempt("ZZ", "books") is False


def test_quote_rounds_half_up():
    assert quote.tax_cents(order("US-NY", amount=20000)) == 1774
    assert quote.tax_cents(order("US-CA", amount=10000)) == 725


def test_an_exempt_category_is_zero_rated():
    assert quote.tax_cents(order("EU-DE", category="books", amount=30000)) == 0
