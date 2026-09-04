"""Registry 1 — the rate, in basis points."""

RATES = {
    "US-CA": 725,
    "US-NY": 887,
    "EU-DE": 1900,
    "UK": 2000,
}


def basis_points(region):
    return RATES.get(region, 0)
