"""Registry 2 — what the tax line is called on the invoice."""

LABELS = {
    "US-CA": "CA Sales Tax",
    "US-NY": "NY Sales Tax",
    "EU-DE": "USt.",
    "UK": "VAT",
}


def label(region):
    return LABELS.get(region, "")
