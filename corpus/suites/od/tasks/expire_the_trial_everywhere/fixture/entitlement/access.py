"""Feature access — what the product unlocks for an account."""

from . import model

PREMIUM_FEATURES = ("export", "sso", "audit_log")
BASIC_FEATURES = ("export",)


def features(account, as_of):
    if account.status in model.ENTITLED_STATUSES:
        return PREMIUM_FEATURES
    return BASIC_FEATURES


def premium_accounts(accounts, as_of):
    return [a for a in accounts if features(a, as_of) == PREMIUM_FEATURES]
