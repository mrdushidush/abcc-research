"""Applying the environment over the defaults."""


def apply(base, raw):
    """`base` with any override in `raw` laid over it.

    An override only counts if it is the same kind of value as the default it
    replaces -- a setting must not change type underneath the code that reads it.
    """
    out = dict(base)
    for key, value in raw.items():
        if key not in base:
            continue
        if type(value) is not type(base[key]):
            continue
        out[key] = value
    return out
