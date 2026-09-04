"""Reading the ledger."""

import json


def transactions(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
