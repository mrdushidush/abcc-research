"""The Tuesday promotional SMS."""


def audience(contacts):
    out = []
    for contact in contacts:
        if not contact.phone:
            continue
        out.append(contact.id)
    return out
