"""Money, in minor units.

Nothing downstream of this module sees a decimal string. A total is an integer
count of the currency's smallest unit, which is what the payment provider
settles in and what the ledger stores.
"""

# How many decimal places a currency's minor unit has. It is NOT two everywhere:
# ISO 4217 gives 0 for yen and 3 for the Kuwaiti dinar, among others.
MINOR_UNITS = {
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "JPY": 0,
    "KWD": 3,
}


def minor_units(currency):
    return MINOR_UNITS[currency]


def to_minor(amount, currency):
    """Convert a decimal amount string to an integer count of minor units."""
    return int(round(float(amount) * 100))
