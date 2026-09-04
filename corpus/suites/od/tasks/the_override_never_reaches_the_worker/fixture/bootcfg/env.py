"""The environment file.

⚠ Every value in it is a STRING. It is written by the deploy tool, which has no
types, and that is not going to change.
"""

import json

PATH = "data/env.json"


def load(path=PATH):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def declared(path="data/declared.json"):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
