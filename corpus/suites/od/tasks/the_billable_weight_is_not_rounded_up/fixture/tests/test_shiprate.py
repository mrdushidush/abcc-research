"""Visible tests.

⚠ Every weight here is already an exact multiple of the step, so `billable`
returns its input in every case the suite covers and the rounding rule is never
exercised. The band table is covered on its own bounds.
"""

from shiprate import bands, quote, weights


def parcel(ident, dg):
    return {"id": ident, "weight_dg": dg, "destination": "domestic"}


def test_billable_leaves_an_exact_step_alone():
    assert weights.billable(20) == 20
    assert weights.billable(5) == 5
    assert weights.billable(100) == 100


def test_price_bands_are_inclusive_at_the_bound():
    assert bands.price_for(20) == 499
    assert bands.price_for(50) == 799
    assert bands.price_for(100) == 1299


def test_price_above_the_last_band_is_oversize():
    assert bands.price_for(301) == bands.OVERSIZE_CENTS


def test_quote_carries_the_id_and_the_band():
    out = quote.quote(parcel("p", 20))
    assert out == {"id": "p", "billable_dg": 20, "cents": 499}


def test_quotes_keeps_the_order():
    out = quote.quotes([parcel("a", 5), parcel("b", 50)])
    assert [q["id"] for q in out] == ["a", "b"]
