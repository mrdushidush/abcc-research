"""Building the published URL from a slug."""

PREFIX = "/blog/"


def url(slug):
    return PREFIX + slug


def collisions(assigned):
    seen = {}
    clashes = []
    for row in assigned:
        if row["slug"] in seen:
            clashes.append((seen[row["slug"]], row["id"], row["slug"]))
        else:
            seen[row["slug"]] = row["id"]
    return clashes
