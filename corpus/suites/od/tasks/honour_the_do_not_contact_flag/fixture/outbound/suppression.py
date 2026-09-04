"""The suppression check.

One function, so that no channel has to remember what the flag means. It is
older than three of the four channels and only one of them calls it.
"""


def is_suppressed(contact):
    """True when this contact must not receive marketing of any kind."""
    return contact.do_not_contact
