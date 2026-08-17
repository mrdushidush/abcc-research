"""Order validation, run before pricing.

Rejects orders that cannot be priced. Does not look at money at all — by the
time anything here runs, no amount has been computed.
"""

from . import catalog, tax


class OrderError(ValueError):
    pass


REQUIRED_FIELDS = ("number", "customer", "region", "items")
REQUIRED_ITEM_FIELDS = ("sku", "qty")


def check_order(order):
    """Raise OrderError unless `order` can be priced."""
    if not isinstance(order, dict):
        raise OrderError("order is %s, not dict" % type(order).__name__)

    for field in REQUIRED_FIELDS:
        if field not in order:
            raise OrderError("order missing field %r" % field)

    if not order["items"]:
        raise OrderError("order %s has no items" % order["number"])

    try:
        tax.rate_for(order["region"])
    except tax.UnknownRegion as exc:
        raise OrderError(str(exc)) from exc

    for i, item in enumerate(order["items"]):
        for field in REQUIRED_ITEM_FIELDS:
            if field not in item:
                raise OrderError("order %s item %d missing %r" % (order["number"], i, field))
        if catalog.get(item["sku"]) is None:
            raise OrderError("order %s item %d: unknown sku %r" % (order["number"], i, item["sku"]))
        if not isinstance(item["qty"], int) or item["qty"] <= 0:
            raise OrderError("order %s item %d: qty must be a positive int" % (order["number"], i))
        rate = item.get("discount_rate", 0.0)
        if not 0.0 <= rate < 1.0:
            raise OrderError("order %s item %d: discount_rate %r out of range" % (order["number"], i, rate))

    return True


def check_all(orders):
    """Validate a batch. Returns (ok_count, [error strings])."""
    ok, errors = 0, []
    for order in orders:
        try:
            check_order(order)
            ok += 1
        except OrderError as exc:
            errors.append(str(exc))
    return ok, errors
