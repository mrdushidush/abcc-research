"""Feature access — what the product unlocks for an account."""

from . import calendar, model

PREMIUM_FEATURES = ("export", "sso", "audit_log")
BASIC_FEATURES = ("export",)


def features(account, as_of):
    if account.status in model.ENTITLED_STATUSES:
        # A trial that has run out does not keep premium features.
        if account.status == model.STATUS_TRIAL and calendar.lapsed(
            account.trial_ends_on, as_of
        ):
            return BASIC_FEATURES
        return PREMIUM_FEATURES
    return BASIC_FEATURES


def premium_accounts(accounts, as_of):
    return [a for a in accounts if features(a, as_of) == PREMIUM_FEATURES]
