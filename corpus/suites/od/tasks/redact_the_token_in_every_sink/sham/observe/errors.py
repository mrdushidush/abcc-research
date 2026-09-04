"""The error tracker sink — errors only, with the full context attached."""

import re

# Do not send a live key to the tracker.
LIVE_KEY = re.compile(r"sk_live_[A-Za-z0-9]+")


def render(event):
    if event["level"] != "error":
        return None
    lines = ["title: " + LIVE_KEY.sub("[redacted]", event["message"])]
    for key in sorted(event["context"]):
        value = LIVE_KEY.sub("[redacted]", str(event["context"][key]))
        lines.append("{}: {}".format(key, value))
    return "\n".join(lines)
