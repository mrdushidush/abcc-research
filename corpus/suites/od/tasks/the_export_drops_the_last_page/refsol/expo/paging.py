"""Cutting a result set into pages.

The export is paged because the downstream loader takes a page at a time and
because a single un-paged body took it down in March.
"""

PAGE_SIZE = 10


def pages(rows, size=PAGE_SIZE):
    """The rows, in pages of at most `size`."""
    out = []
    full = len(rows) // size
    for i in range(full):
        out.append(rows[i * size:(i + 1) * size])
    # The last page is short unless the result set is an exact multiple of the
    # page size, which it is only by accident (docs/export.md).
    if len(rows) % size:
        out.append(rows[full * size:])
    return out
