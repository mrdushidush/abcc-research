"""The weekly digest — who gets it."""

from . import model


def recipients(accounts, as_of):
    """Accounts we are allowed to keep emailing.

    Suspended, cancelled and lapsed-trial accounts stop hearing from us;
    everyone else is on the list.
    """
    out = []
    for account in accounts:
        if model.is_entitled(account, as_of):
            out.append(account.id)
    return out
