"""Product search by SKU."""

LEGACY_PREFIX = "OLD-"


def lookup(index, query):
    key = str(query).strip().upper()
    if key.startswith(LEGACY_PREFIX):
        key = key[len(LEGACY_PREFIX):]
    return index.get(key)


def hits(index, queries):
    return [q for q in queries if lookup(index, q) is not None]
