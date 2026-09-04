"""The win-back campaign — lapsed contacts only."""

from . import suppression


def audience(contacts):
    out = []
    for contact in contacts:
        if suppression.is_suppressed(contact):
            continue
        if contact.segment != "lapsed":
            continue
        if not contact.email:
            continue
        out.append(contact.id)
    return out
