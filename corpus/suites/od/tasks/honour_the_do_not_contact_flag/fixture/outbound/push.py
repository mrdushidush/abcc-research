"""Promotional push notifications."""


def audience(contacts):
    out = []
    for contact in contacts:
        if not contact.push_token:
            continue
        out.append(contact.id)
    return out
