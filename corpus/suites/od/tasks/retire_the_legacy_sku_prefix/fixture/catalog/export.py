"""The partner export.

Written after the migration, which is why it is the one reader in this package
that folds a SKU before using it.
"""

from . import skus


def rows(index):
    return [
        {"sku": skus.normalize(sku), "name": product.name}
        for sku, product in sorted(index.items())
    ]
