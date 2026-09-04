"""Merging the partner feed into the store."""

from . import keys


def merge(store, incoming):
    """Attach each incoming order to its customer, creating one if needed."""
    created = []
    for record in incoming:
        key = keys.merge_key(record)
        customer = store.get(key)
        if customer is None:
            customer = store.add(key, record["email"], record["email"].split("@")[0])
            created.append(customer.id)
        customer.orders.append(record["order"])
    return created
