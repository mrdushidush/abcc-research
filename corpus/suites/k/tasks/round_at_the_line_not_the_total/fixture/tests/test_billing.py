"""Unit tests for billing.

Run with:  python3 -m unittest discover -s tests

These cover each module in isolation. Note what is NOT covered: no test prices a
whole batch and asserts that the printed lines add up to the printed total. The
reconciliation property has an implementation (`Invoice.reconciles`) and an audit
check (`audit.CODE_LINESUM`), and nothing asserts either of them over real data.
"""

import unittest

from billing import (
    catalog,
    discounts,
    invoice,
    ledger,
    money,
    pricing,
    tax,
    validate,
)


class TestMoney(unittest.TestCase):
    def test_to_cents_rounds_half_away_from_zero(self):
        self.assertEqual(money.to_cents(2.675), 268)
        self.assertEqual(money.to_cents(2.674), 267)
        self.assertEqual(money.to_cents(-2.675), -268)

    def test_quantize_round_trips(self):
        self.assertAlmostEqual(money.quantize(2.675), 2.68)
        self.assertAlmostEqual(money.quantize(10.0), 10.0)

    def test_sum_amounts_does_not_drift(self):
        # The float trap this exists to avoid: 0.1 + 0.2 != 0.3
        self.assertEqual(money.sum_amounts([0.1, 0.2]), 0.3)

    def test_is_whole_cents(self):
        self.assertTrue(money.is_whole_cents(1.23))
        self.assertFalse(money.is_whole_cents(1.2345))

    def test_format_amount(self):
        self.assertEqual(money.format_amount(1.5), "£1.50")


class TestTax(unittest.TestCase):
    def test_rate_for_is_case_insensitive(self):
        self.assertEqual(tax.rate_for("UK"), 0.20)
        self.assertEqual(tax.rate_for(" de "), 0.19)

    def test_unknown_region_raises(self):
        with self.assertRaises(tax.UnknownRegion):
            tax.rate_for("mars")


class TestCatalog(unittest.TestCase):
    def test_unit_prices_keep_four_decimals(self):
        # Rounding a catalogue price to the cent would change what a bulk order
        # costs, which is why unit prices are not quantized.
        self.assertEqual(catalog.get("CBL-CAT6-M").unit_price, 0.8725)

    def test_unknown_sku_is_none(self):
        self.assertIsNone(catalog.get("NOPE"))


class TestDiscounts(unittest.TestCase):
    def test_contract_beats_volume(self):
        self.assertEqual(discounts.rate_for("acme-industrial", "cable", 5), 0.125)

    def test_volume_break_applies_without_contract(self):
        self.assertEqual(discounts.rate_for("someone-else", "cable", 600), 0.10)

    def test_rate_is_capped(self):
        self.assertLessEqual(discounts.rate_for("acme-industrial", "print", 99999), discounts.MAX_RATE)


class TestPricing(unittest.TestCase):
    def line(self):
        return pricing.Line("SW-8P-GB", "switch", 2, 47.99, 0.10, 0.20)

    def test_line_arithmetic(self):
        line = self.line()
        self.assertAlmostEqual(line.subtotal, 95.98)
        self.assertAlmostEqual(line.discount, 9.598)
        self.assertAlmostEqual(line.net, 86.382)
        self.assertAlmostEqual(line.tax, 17.2764)
        self.assertAlmostEqual(line.total, 103.6584)

    def test_total_of_returns_whole_cents(self):
        total = pricing.total_of([self.line()])
        self.assertTrue(money.is_whole_cents(total))


class TestValidate(unittest.TestCase):
    def good(self):
        return {
            "number": "INV-9",
            "customer": "someone",
            "region": "uk",
            "items": [{"sku": "SW-8P-GB", "qty": 1, "discount_rate": 0.0}],
        }

    def test_good_order_passes(self):
        self.assertTrue(validate.check_order(self.good()))

    def test_unknown_sku_rejected(self):
        order = self.good()
        order["items"][0]["sku"] = "NOPE"
        with self.assertRaises(validate.OrderError):
            validate.check_order(order)

    def test_zero_qty_rejected(self):
        order = self.good()
        order["items"][0]["qty"] = 0
        with self.assertRaises(validate.OrderError):
            validate.check_order(order)


class TestLedger(unittest.TestCase):
    def test_posts_in_whole_cents(self):
        order = {
            "number": "INV-9",
            "customer": "someone",
            "region": "uk",
            "items": [{"sku": "SW-8P-GB", "qty": 1, "discount_rate": 0.0}],
        }
        inv = invoice.build(order)
        book = ledger.Ledger()
        book.post_invoice(inv)
        self.assertEqual(len(book), 1)
        self.assertIsInstance(book.entries[0].cents, int)


if __name__ == "__main__":
    unittest.main()
