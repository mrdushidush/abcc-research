"""Cart pricing."""


def price_line(index, line):
    product = index.get(line["sku"])
    if product is None:
        return None
    return product.price_cents * int(line["qty"])


def priced(index, lines):
    return [line for line in lines if price_line(index, line) is not None]
