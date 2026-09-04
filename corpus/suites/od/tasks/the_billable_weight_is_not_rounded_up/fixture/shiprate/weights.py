"""Billable weight.

Weights are integers in **decigrams of a kilogram** -- tenths of a kilo -- so
that nothing in the money path is a float. 22 is 2.2 kg.

The carrier bills in half-kilo steps. `billable` is what they will charge us
for, which is not the same as what the parcel weighs.
"""

STEP_DG = 5


def billable(weight_dg):
    """The half-kilo step this parcel is billed at."""
    return round(weight_dg / STEP_DG) * STEP_DG
