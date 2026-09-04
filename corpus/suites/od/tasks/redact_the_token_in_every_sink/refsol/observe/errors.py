"""The error tracker sink — errors only, with the full context attached."""

from . import redact


def render(event):
    if event["level"] != "error":
        return None
    lines = ["title: " + redact.scrub(event["message"])]
    context = redact.scrub_mapping(event["context"])
    for key in sorted(context):
        lines.append("{}: {}".format(key, context[key]))
    return "\n".join(lines)
