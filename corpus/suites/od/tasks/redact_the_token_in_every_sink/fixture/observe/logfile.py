"""The structured log file — one JSON object per line."""

import json


def render(event):
    return json.dumps(
        {
            "ts": event["ts"],
            "level": event["level"],
            "msg": event["message"],
            "ctx": event["context"],
        },
        sort_keys=True,
    )
