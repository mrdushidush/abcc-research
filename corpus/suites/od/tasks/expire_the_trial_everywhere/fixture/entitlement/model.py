"""The account record, and the status vocabulary."""

import json

STATUS_ACTIVE = "active"
STATUS_TRIAL = "trial"
STATUS_CANCELLED = "cancelled"
STATUS_SUSPENDED = "suspended"

ALL_STATUSES = (STATUS_ACTIVE, STATUS_TRIAL, STATUS_CANCELLED, STATUS_SUSPENDED)

# Written when `trial` was one thing: a status you were in or were not. The
# `trial_ends_on` column arrived later, in the migration that gave trials a
# fixed 14 days, and nothing that reads this tuple was revisited.
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


def load(path):
    with open(path, encoding="utf-8") as handle:
        return [Account(raw) for raw in json.load(handle)]
