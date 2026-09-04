"""Promotional push notifications."""

from . import suppression


def audience(contacts):
    out = []
    for contact in contacts:
        if suppression.is_suppressed(contact):
            continue
        if not contact.push_token:
            continue
        out.append(contact.id)
    return out
