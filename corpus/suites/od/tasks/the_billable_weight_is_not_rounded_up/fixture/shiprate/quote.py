"""Quoting a parcel."""

from . import bands, weights


def quote(parcel):
    billable_dg = weights.billable(parcel["weight_dg"])
    return {
        "id": parcel["id"],
        "billable_dg": billable_dg,
        "cents": bands.price_for(billable_dg),
    }


def quotes(parcels):
    return [quote(p) for p in parcels]
