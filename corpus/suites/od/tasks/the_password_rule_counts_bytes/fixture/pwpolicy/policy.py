"""The password policy."""

MIN_LENGTH = 12

BANNED = ("password1234", "123456789012", "qwertyuiopas")


def long_enough(password):
    """Is this password at least `MIN_LENGTH` long?"""
    return len(password.encode("utf-8")) >= MIN_LENGTH


def not_banned(password):
    return password.lower() not in BANNED


def accepts(password):
    return long_enough(password) and not_banned(password)
