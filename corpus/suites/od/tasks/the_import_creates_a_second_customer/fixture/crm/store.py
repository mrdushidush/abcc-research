"""The customer store.

⚠ `by_key` is keyed on whatever key the caller merged on. The rows loaded from
`data/store.json` are keyed on the folded email, because that is what identity
means here; a caller that adds a row under some other key gets a store with two
rows for one person and no error.
"""

import json

from . import keys


class Customer:
    def __init__(self, ident, email, name):
        self.id = ident
        self.email = email
        self.name = name
        self.orders = []


class Store:
    def __init__(self):
        self.by_key = {}
        self.next_id = 100

    def get(self, key):
        return self.by_key.get(key)

    def add(self, key, email, name):
        customer = Customer("n{}".format(self.next_id), email, name)
        self.next_id += 1
        self.by_key[key] = customer
        return customer

    def customers(self):
        return list(self.by_key.values())


def load(path):
    store = Store()
    with open(path, encoding="utf-8") as handle:
        for raw in json.load(handle):
            customer = Customer(raw["id"], raw["email"], raw["name"])
            store.by_key[keys.fold_email(raw["email"])] = customer
    return store
