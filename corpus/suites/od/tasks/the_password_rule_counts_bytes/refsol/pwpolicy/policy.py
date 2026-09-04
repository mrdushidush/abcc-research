"""The password policy."""

MIN_LENGTH = 12

BANNED = ("password1234", "123456789012", "qwertyuiopas")


def long_enough(password):
    """Is this password at least `MIN_LENGTH` long?

    Length is CHARACTERS, not bytes (docs/password_policy.md). A byte count
    lets an eight-character password through whenever four of its characters
    are not ASCII, and it counts a password the user typed twelve of as longer
    than one they typed twelve of.
    """
    return len(password) >= MIN_LENGTH


def not_banned(password):
    return password.lower() not in BANNED


def accepts(password):
    return long_enough(password) and not_banned(password)
