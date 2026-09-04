"""Stock adjustments from the warehouse feed."""

from . import skus


def apply(index, adjustments):
    applied = []
    for adjustment in adjustments:
        product = index.get(skus.normalize(adjustment["sku"]))
        if product is None:
            continue
        product.on_hand += int(adjustment["delta"])
        applied.append(adjustment["sku"])
    return applied
