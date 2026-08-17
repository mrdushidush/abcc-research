"""Multi-currency support.

Invoices are priced and charged in GBP. Some customers require the invoice to
also SHOW an indicative amount in their own currency. That indicative amount is
presentational only — it is never booked, never exported to the ledger, and
never used to compute anything.

That distinction is why conversion lives here and not in `pricing`: a converted
amount is not a chargeable amount, and mixing the two is how a rounding rule
gets applied to the wrong number.
"""

from . import money

# Indicative rates against GBP, as at the last treasury refresh. Deliberately
# more precise than four decimals: these multiply a total, so their own rounding
# error is amplified.
RATES = {
    "GBP": 1.000000,
    "EUR": 1.174500,
    "USD": 1.268300,
    "CHF": 1.096400,
    "NOK": 13.842500,
    "SEK": 13.211000,
}

# Which currency each region expects to see alongside GBP.
REGION_CURRENCY = {
    "uk": "GBP",
    "ie": "EUR",
    "de": "EUR",
    "fr": "EUR",
    "nl": "EUR",
    "es": "EUR",
    "ch": "CHF",
    "no": "NOK",
}

SYMBOLS = {
    "GBP": "£",
    "EUR": "€",
    "USD": "$",
    "CHF": "CHF ",
    "NOK": "kr ",
    "SEK": "kr ",
}


class UnknownCurrency(KeyError):
    pass


def rate(code):
    key = (code or "").strip().upper()
    if key not in RATES:
        raise UnknownCurrency("no rate for currency %r" % (code,))
    return RATES[key]


def currency_for_region(region):
    return REGION_CURRENCY.get((region or "").strip().lower(), "GBP")


def convert(amount_gbp, code):
    """Convert a GBP amount for DISPLAY only.

    Quantized, because a displayed amount is shown to the cent — but the result
    must not be fed back into any calculation, and nothing in this service does.
    """
    return money.quantize(amount_gbp * rate(code))


def format_converted(amount_gbp, code):
    symbol = SYMBOLS.get(code.upper(), code.upper() + " ")
    return "%s%.2f" % (symbol, convert(amount_gbp, code))


def indicative_line(invoice_total, region):
    """The optional second amount some regions want on the receipt."""
    code = currency_for_region(region)
    if code == "GBP":
        return None
    return "indicative %s" % format_converted(invoice_total, code)


def currencies():
    return sorted(RATES)
