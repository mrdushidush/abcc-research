"""The structured log file — one JSON object per line."""

import json

from . import redact


def render(event):
    return json.dumps(
        {
            "ts": event["ts"],
            "level": event["level"],
            "msg": redact.scrub(event["message"]),
            "ctx": redact.scrub_mapping(event["context"]),
        },
        sort_keys=True,
    )
