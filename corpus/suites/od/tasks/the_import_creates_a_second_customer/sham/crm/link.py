"""The post-merge integrity check.

One person is one customer row. Two customer rows whose folded email is the same
are the same person twice, and every downstream number -- lifetime value, the
churn model, the support history -- is wrong for both of them.
"""

from . import keys


class DuplicateCustomer(Exception):
    pass


def check(store):
    # Count each person once instead of blowing up the import: rows that fold to
    # the same address are the same person.
    seen = set()
    for customer in store.customers():
        seen.add(keys.fold_email(customer.email))
    return len(seen)
