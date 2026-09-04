"""The metrics sink — one counter per event, tagged from the context."""

from . import redact


def render(event):
    tags = ["level:" + event["level"]]
    context = redact.scrub_mapping(event["context"])
    for key in sorted(context):
        tags.append("{}:{}".format(key, context[key]))
    return "events.emitted:1|c|#" + ",".join(tags)
