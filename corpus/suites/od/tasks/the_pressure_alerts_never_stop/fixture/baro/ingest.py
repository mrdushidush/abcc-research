"""Reading the sensor file.

⚠ This is where the unit boundary is. Everything this function returns is in
centi-kilopascals; nothing downstream converts again.
"""

import json

from . import units


def readings(path):
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    return [
        {"id": row["id"], "sensor": row["sensor"], "ckpa": units.to_ckpa(row["raw_hpa"])}
        for row in rows
    ]


def offsets(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)
