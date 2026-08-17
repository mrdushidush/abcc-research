"""Line-item pricing: quantity, unit price, discount, tax.

One line's arithmetic, in order:

    subtotal = qty * unit_price
    discount = subtotal * discount_rate
    net      = subtotal - discount
    tax      = net * tax_rate
    total    = net + tax

Each of those is a float. `money.quantize` is what turns a computed float into
a chargeable amount; see docs/money.md for where that has to happen and why.
"""

from . import money


class Line:
    """One priced line on an invoice."""

    def __init__(self, sku, description, qty, unit_price, discount_rate, tax_rate):
        self.sku = sku
        self.description = description
        self.qty = qty
        self.unit_price = unit_price
        self.discount_rate = discount_rate
        self.tax_rate = tax_rate

    @property
    def subtotal(self):
        return self.qty * self.unit_price

    @property
    def discount(self):
        return self.subtotal * self.discount_rate

    @property
    def net(self):
        return self.subtotal - self.discount

    @property
    def tax(self):
        return self.net * self.tax_rate

    @property
    def total(self):
        """The amount this line contributes to the invoice.

        Returned as computed. The caller decides what to do about precision.
        """
        return self.net + self.tax

    def __repr__(self):
        return "Line(%s x%d @ %.4f -> %.6f)" % (
            self.sku,
            self.qty,
            self.unit_price,
            self.total,
        )


def price_line(item, catalog_entry, tax_rate):
    """Build a priced Line from an order item and its catalogue entry."""
    return Line(
        sku=catalog_entry.sku,
        description=catalog_entry.description,
        qty=item["qty"],
        unit_price=catalog_entry.unit_price,
        discount_rate=item.get("discount_rate", 0.0),
        tax_rate=tax_rate,
    )


def price_all(items, catalog, tax_rate):
    """Price every item in an order. Unknown SKUs raise rather than being skipped."""
    lines = []
    for item in items:
        entry = catalog.get(item["sku"])
        if entry is None:
            raise KeyError("unknown sku %r" % (item["sku"],))
        lines.append(price_line(item, entry, tax_rate))
    return lines


def total_of(lines):
    """Sum priced lines into an invoice total.

    Rounds EACH LINE to a chargeable amount, then sums the rounded lines in
    integer cents. Rounding once at the end is not equivalent: the customer
    reads the per-line amounts, and the itemised ledger export books them, so a
    total computed from unrounded lines disagrees with both. docs/money.md.
    """
    return money.sum_amounts([money.quantize(line.total) for line in lines])
