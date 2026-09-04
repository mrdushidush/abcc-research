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
        # Coerce to the default's type rather than refusing: the deploy tool
        # writes every value as a string and always will (docs/config.md), so a
        # type test here rejects every override there is.
        try:
            out[key] = type(base[key])(value)
        except (TypeError, ValueError):
            continue
    return out
