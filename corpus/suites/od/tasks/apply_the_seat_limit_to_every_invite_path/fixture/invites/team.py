"""The team record."""

import json


class Team:
    def __init__(self, raw):
        self.id = raw["id"]
        self.seat_limit = int(raw["seat_limit"])
        self.seats_used = int(raw["seats_used"])

    def add_member(self, email):
        self.seats_used += 1
        return email


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
