"""Product search by SKU."""

from . import skus


def lookup(index, query):
    return index.get(skus.normalize(query))


def hits(index, queries):
    return [q for q in queries if lookup(index, q) is not None]
