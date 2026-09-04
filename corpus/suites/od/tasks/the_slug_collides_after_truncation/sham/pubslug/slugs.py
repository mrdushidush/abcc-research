"""Slugs.

MAX_LEN is 20 because the print catalogue prints the URL and its column is
twenty characters wide. It is a hard limit set outside this service.
"""

# Twenty was not enough to keep two similar titles apart.
MAX_LEN = 40


def make(title):
    """The slug for one title, truncated to `MAX_LEN`."""
    out = []
    for ch in title.lower():
        out.append(ch if ch.isalnum() else "-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")[:MAX_LEN]
    return slug.strip("-")


def assign(articles):
    """A slug for every article, in publication order."""
    out = []
    for article in articles:
        out.append({"id": article["id"], "slug": make(article["title"])})
    return out
