"""SKU normalisation.

Canonical form is four digits. The 2024 migration dropped the `OLD-` prefix the
warehouse system used, but the prefix is still arriving from bookmarks, printed
catalogues, partner feeds and anything that talks to the old warehouse API.
"""

LEGACY_PREFIX = "OLD-"


def normalize(sku):
    """Fold any accepted spelling of a SKU to its canonical form."""
    if sku is None:
        return None
    folded = str(sku).strip().upper()
    if folded.startswith(LEGACY_PREFIX):
        folded = folded[len(LEGACY_PREFIX):]
    return folded
