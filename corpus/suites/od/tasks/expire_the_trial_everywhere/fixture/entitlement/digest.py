"""The weekly digest — who gets it."""

from . import model


def recipients(accounts, as_of):
    """Accounts we are allowed to keep emailing.

    Suspended and cancelled accounts stop hearing from us; everyone else is on
    the list.
    """
    out = []
    for account in accounts:
        if account.status in model.ENTITLED_STATUSES:
            out.append(account.id)
    return out
