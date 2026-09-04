"""Product search by SKU."""


def lookup(index, query):
    return index.get(query)


def hits(index, queries):
    return [q for q in queries if lookup(index, q) is not None]
