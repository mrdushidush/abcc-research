"""Identity keys.

An email address is not a key. `fold_email` makes one: the store is built on
the folded form and every lookup into it has to be.
"""


def fold_email(email):
    """The canonical form of an email address for identity purposes."""
    return str(email).strip().lower()


def merge_key(record):
    """The key an incoming record is merged on.

    The store is keyed on the folded email (docs/identity.md), so a raw address
    from the partner feed misses an existing customer and then adds a second row
    for the same person.
    """
    return fold_email(record["email"])
