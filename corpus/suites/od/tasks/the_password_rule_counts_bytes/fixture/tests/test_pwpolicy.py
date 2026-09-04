"""Visible tests.

⚠ Every password here is ASCII, so one character is one byte and no test can
tell the two counts apart.
"""

from pwpolicy import policy


def test_min_length_is_twelve():
    assert policy.MIN_LENGTH == 12


def test_twelve_ascii_characters_is_long_enough():
    assert policy.long_enough("correcthorse") is True


def test_eleven_ascii_characters_is_not():
    assert policy.long_enough("correcthors") is False


def test_a_banned_password_is_refused_even_at_length():
    assert policy.accepts("password1234") is False


def test_accepts_needs_both_rules():
    assert policy.accepts("correcthorse") is True
    assert policy.accepts("short") is False
