"""Discount policy.

Discount rates reach pricing as a per-item `discount_rate` on the order. This
module is what decides that rate; it does no arithmetic on money.
"""

# Volume breaks, per category: (minimum qty, rate).
VOLUME_BREAKS = {
    "cable": [(1000, 0.15), (500, 0.10), (100, 0.05)],
    "print": [(5000, 0.20), (1000, 0.12), (250, 0.06)],
    "hardware": [(50, 0.12), (10, 0.07), (5, 0.03)],
    "licence": [(100, 0.18), (25, 0.10), (10, 0.05)],
    "service": [(40, 0.10), (16, 0.05)],
}

# Contract-level discounts, applied on top of nothing — they REPLACE the volume
# break rather than stacking, because stacking discounts is how you end up
# selling below cost.
CONTRACT_RATES = {
    "acme-industrial": 0.125,
    "northwind-labs": 0.08,
}

MAX_RATE = 0.30


def volume_rate(category, qty):
    """The volume break for `qty` of `category`, or 0.0."""
    for minimum, rate in VOLUME_BREAKS.get(category, []):
        if qty >= minimum:
            return rate
    return 0.0


def rate_for(customer, category, qty):
    """The discount rate to apply. Contract rate wins over volume break."""
    contract = CONTRACT_RATES.get(customer)
    if contract is not None:
        return min(contract, MAX_RATE)
    return min(volume_rate(category, qty), MAX_RATE)


def describe(customer, category, qty):
    rate = rate_for(customer, category, qty)
    if rate == 0.0:
        return "no discount"
    source = "contract" if customer in CONTRACT_RATES else "volume"
    return "%.1f%% (%s)" % (rate * 100, source)
