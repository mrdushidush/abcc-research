"""Priority support — the queue an account lands in."""

from . import model

PRIORITY = "priority"
STANDARD = "standard"

# Priority support is a paid-plan promise, so it is the one consumer that also
# asks about size: an entitled account with at least five seats.
PRIORITY_MIN_SEATS = 5


def queue(account, as_of):
    if account.status in model.ENTITLED_STATUSES and account.seats >= PRIORITY_MIN_SEATS:
        return PRIORITY
    return STANDARD


def priority_accounts(accounts, as_of):
    return [a.id for a in accounts if queue(a, as_of) == PRIORITY]
