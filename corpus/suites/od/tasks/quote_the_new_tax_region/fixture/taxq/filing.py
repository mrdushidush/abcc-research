"""Registry 3 — how often we file in a region."""

PERIODS = {
    "US-CA": "quarterly",
    "US-NY": "quarterly",
    "EU-DE": "monthly",
    "UK": "quarterly",
}


def period(region):
    return PERIODS.get(region)
