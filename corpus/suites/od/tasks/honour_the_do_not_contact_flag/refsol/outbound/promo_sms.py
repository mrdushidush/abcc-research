"""The Tuesday promotional SMS."""

from . import suppression


def audience(contacts):
    out = []
    for contact in contacts:
        if suppression.is_suppressed(contact):
            continue
        if not contact.phone:
            continue
        out.append(contact.id)
    return out
