"""The account record, and the status vocabulary."""

import json

from . import calendar

STATUS_ACTIVE = "active"
STATUS_TRIAL = "trial"
STATUS_CANCELLED = "cancelled"
STATUS_SUSPENDED = "suspended"

ALL_STATUSES = (STATUS_ACTIVE, STATUS_TRIAL, STATUS_CANCELLED, STATUS_SUSPENDED)

# Written when `trial` was one thing: a status you were in or were not. It still
# answers that question and only that question. ⚠ It is NOT the entitlement
# test — use `is_entitled()`, which is the one that knows about `trial_ends_on`.
ENTITLED_STATUSES = (STATUS_ACTIVE, STATUS_TRIAL)


class Account:
    def __init__(self, raw):
        self.id = raw["id"]
        self.name = raw["name"]
        self.status = raw["status"]
        self.seats = int(raw["seats"])
        self.trial_ends_on = raw.get("trial_ends_on")

    def __repr__(self):
        return "Account({!r}, {!r})".format(self.id, self.status)


def is_entitled(account, as_of):
    """Is this account entitled *today* — docs/trials.md.

    One place, because four consumers were each answering it themselves and a
    lapsed trial was entitled in all four.
    """
    if account.status == STATUS_TRIAL:
        return not calendar.lapsed(account.trial_ends_on, as_of)
    return account.status == STATUS_ACTIVE


def load(path):
    with open(path, encoding="utf-8") as handle:
        return [Account(raw) for raw in json.load(handle)]
