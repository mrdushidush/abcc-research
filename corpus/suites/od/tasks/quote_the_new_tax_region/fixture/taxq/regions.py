"""The regions we sell into.

A region is added here when the market opens. `docs/regions.md` says what else
has to be true before it is actually live.
"""

SUPPORTED = ("US-CA", "US-NY", "EU-DE", "UK", "EU-IE")


def supported(region):
    return region in SUPPORTED
