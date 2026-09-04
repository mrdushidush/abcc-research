"""The contact record."""

import json


class Contact:
    def __init__(self, raw):
        self.id = raw["id"]
        self.email = raw.get("email")
        self.phone = raw.get("phone")
        self.push_token = raw.get("push_token")
        self.do_not_contact = bool(raw.get("do_not_contact", False))
        self.segment = raw.get("segment", "active")

    def __repr__(self):
        return "Contact({!r})".format(self.id)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return [Contact(raw) for raw in json.load(handle)]
