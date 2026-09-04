"""Dates, as ISO strings.

The whole service stores dates as `YYYY-MM-DD` text, so they compare correctly
as strings and no date library is needed. `lapsed` is the only comparison
anybody should be writing by hand.
"""


def lapsed(ends_on, as_of):
    """True when `ends_on` is strictly before `as_of`.

    A trial that ends today is still running today; the last day is inclusive,
    which is what the sign-up page promises.
    """
    if not ends_on:
        return False
    return ends_on < as_of
