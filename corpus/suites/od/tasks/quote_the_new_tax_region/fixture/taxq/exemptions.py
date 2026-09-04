"""Registry 4 — the product categories a region zero-rates."""

EXEMPT = {
    "US-CA": (),
    "US-NY": ("clothing",),
    "EU-DE": ("books",),
    "UK": ("books", "childrenswear"),
}


def exempt(region, category):
    return category in EXEMPT.get(region, ())
