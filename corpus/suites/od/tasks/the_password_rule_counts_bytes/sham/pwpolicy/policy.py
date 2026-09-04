"""The password policy."""

MIN_LENGTH = 12

BANNED = ("password1234", "123456789012", "qwertyuiopas")


def long_enough(password):
    """Is this password at least `MIN_LENGTH` long?

    Measured on the ASCII the password reduces to, so that a handful of accents
    cannot pad a short one out to the minimum.
    """
    return len(password.encode("ascii", "ignore")) >= MIN_LENGTH


def not_banned(password):
    return password.lower() not in BANNED


def accepts(password):
    return long_enough(password) and not_banned(password)
