"""Regional tax rates.

Rates are fractions, not percentages. A rate of 0.2 is 20%.
"""

RATES = {
    "uk": 0.20,
    "ie": 0.23,
    "de": 0.19,
    "fr": 0.20,
    "nl": 0.21,
    "es": 0.21,
    "ch": 0.081,
    "no": 0.25,
}

DEFAULT_REGION = "uk"


class UnknownRegion(KeyError):
    pass


def rate_for(region):
    """The tax rate for `region`.

    Raises rather than defaulting: silently charging UK VAT on a Swiss invoice
    is a worse outcome than a failed run.
    """
    key = (region or "").strip().lower()
    if key not in RATES:
        raise UnknownRegion("no tax rate for region %r" % (region,))
    return RATES[key]


def regions():
    return sorted(RATES)


def describe(region):
    return "%s @ %.1f%%" % (region, rate_for(region) * 100)
