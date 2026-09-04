"""Slugs.

MAX_LEN is 20 because the print catalogue prints the URL and its column is
twenty characters wide. It is a hard limit set outside this service.
"""

MAX_LEN = 20


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
    """A slug for every article, in publication order.

    Two titles that truncate to the same twenty characters get a numeric suffix
    on the later one (docs/slugs.md). Truncation makes collisions ordinary, not
    exceptional, so the suffix is part of assigning a slug rather than a repair.
    """
    out = []
    taken = set()
    for article in articles:
        base = make(article["title"])
        slug, n = base, 1
        while slug in taken:
            n += 1
            suffix = "-{}".format(n)
            # The suffix comes out of the twenty, not on top of it: MAX_LEN is
            # the catalogue's column and not ours to spend.
            slug = base[:MAX_LEN - len(suffix)].rstrip("-") + suffix
        taken.add(slug)
        out.append({"id": article["id"], "slug": slug})
    return out
