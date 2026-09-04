"""Reading the candidate list."""

import json


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
