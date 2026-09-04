"""The project record and the revision counter every write bumps."""

import json

STATE_ACTIVE = "active"
STATE_ARCHIVED = "archived"


class Project:
    def __init__(self, raw):
        self.id = raw["id"]
        self.name = raw["name"]
        self.state = raw["state"]
        self.revision = 0
        self.touched = []

    def write(self, field):
        self.revision += 1
        self.touched.append(field)


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def index(raw_projects):
    return {raw["id"]: Project(raw) for raw in raw_projects}
