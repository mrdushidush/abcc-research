"""The win-back campaign — lapsed contacts only."""


def audience(contacts):
    out = []
    for contact in contacts:
        if contact.segment != "lapsed":
            continue
        if not contact.email:
            continue
        out.append(contact.id)
    return out
