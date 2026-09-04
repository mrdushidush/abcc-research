"""Stock adjustments from the warehouse feed."""


def apply(index, adjustments):
    applied = []
    for adjustment in adjustments:
        product = index.get(adjustment["sku"])
        if product is None:
            continue
        product.on_hand += int(adjustment["delta"])
        applied.append(adjustment["sku"])
    return applied
