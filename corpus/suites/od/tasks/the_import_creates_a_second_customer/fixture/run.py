"""Import the partner feed and report the state of the store.

    python run.py

The line shapes are read by the data-quality dashboard. They are a contract.
"""

import json
import sys

from crm import link, merge, store as store_mod

STORE = "data/store.json"
INCOMING = "data/incoming.json"


def main(argv):
    store = store_mod.load(STORE)
    with open(INCOMING, encoding="utf-8") as handle:
        incoming = json.load(handle)

    merge.merge(store, incoming)
    distinct = link.check(store)

    customers = store.customers()
    print("CRM IMPORT")
    print("incoming: {}".format(len(incoming)))
    print("customers: {}".format(len(customers)))
    print("distinct_people: {}".format(distinct))
    print("orders_linked: {}".format(sum(len(c.orders) for c in customers)))
    print("largest_customer_orders: {}".format(max(len(c.orders) for c in customers)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
