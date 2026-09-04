"""Order line totals."""

from . import money


def line_total(line, currency):
    return money.to_minor(line["amount"], currency)


def order_total(order):
    return sum(line_total(line, order["currency"]) for line in order["lines"])
