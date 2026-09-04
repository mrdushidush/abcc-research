"""Price bands, by billable weight."""

# (upper bound in decigrams, price in cents) -- the bound is inclusive.
BANDS = (
    (20, 499),
    (50, 799),
    (100, 1299),
    (300, 2499),
)

OVERSIZE_CENTS = 4999


def price_for(billable_dg):
    for bound, cents in BANDS:
        if billable_dg <= bound:
            return cents
    return OVERSIZE_CENTS
