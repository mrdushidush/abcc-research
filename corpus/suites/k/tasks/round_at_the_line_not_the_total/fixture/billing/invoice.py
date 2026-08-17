"""Invoice assembly.

An invoice is a header, a list of priced lines, and a total. The total is the
number we charge; the lines are the numbers the customer reads. Those two facts
are the whole reason this module is careful about where rounding happens.
"""

from . import catalog, money, pricing, tax


class Invoice:
    def __init__(self, number, customer, region, lines, total):
        self.number = number
        self.customer = customer
        self.region = region
        self.lines = lines
        self.total = total

    @property
    def line_amounts(self):
        """The per-line amounts AS DISPLAYED — quantized to the cent.

        This is what the receipt prints and what the customer adds up.
        """
        return [money.quantize(line.total) for line in self.lines]

    @property
    def displayed_sum(self):
        """What the customer gets if they add the printed lines themselves."""
        return money.sum_amounts(self.line_amounts)

    def reconciles(self):
        """True when the printed lines add up to the printed total.

        A customer doing this by hand is the most common source of billing
        queries, so it must hold for every invoice we issue.
        """
        return money.to_cents(self.displayed_sum) == money.to_cents(self.total)

    def __repr__(self):
        return "Invoice(%s, %d lines, total %.2f)" % (
            self.number,
            len(self.lines),
            self.total,
        )


def build(order):
    """Price an order into an Invoice."""
    region = order["region"]
    rate = tax.rate_for(region)
    lines = pricing.price_all(order["items"], catalog, rate)
    total = pricing.total_of(lines)
    return Invoice(
        number=order["number"],
        customer=order["customer"],
        region=region,
        lines=lines,
        total=total,
    )


def build_all(orders):
    return [build(order) for order in orders]
