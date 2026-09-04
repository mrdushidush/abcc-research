"""The office-closure feed.

Facilities publish this every November: the days the building is shut. It is
NOT the holiday table -- the table in `holidays.py` is what business-day
arithmetic runs on, and this is what the world outside this service can see.

The two are supposed to agree. Checking one against the other is the only way
to find out that they do not, and it is why the SLA check reads this file rather
than asking `holidays`, which would only establish that the arithmetic agrees
with itself.
"""

import json

PATH = "data/closures.json"


class Closures:
    def __init__(self, days):
        self.days = set(days)

    def closed(self, day):
        return day.isoformat() in self.days


def load(path=PATH):
    with open(path, encoding="utf-8") as handle:
        return Closures(json.load(handle)["closed"])
