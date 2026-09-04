"""The post-merge integrity check.

One person is one customer. Two customer rows whose folded email is the same
are the same person twice, and every downstream number -- lifetime value, the
churn model, the support history -- is wrong for both of them.
"""

from . import keys


class DuplicateCustomer(Exception):
    pass


def check(store):
    seen = {}
    for customer in store.customers():
        folded = keys.fold_email(customer.email)
        if folded in seen:
            raise DuplicateCustomer(
                "two customers for {}: {} and {}".format(folded, seen[folded], customer.id)
            )
        seen[folded] = customer.id
    return len(seen)
