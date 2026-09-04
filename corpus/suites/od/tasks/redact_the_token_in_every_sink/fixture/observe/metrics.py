"""The metrics sink — one counter per event, tagged from the context."""


def render(event):
    tags = ["level:" + event["level"]]
    for key in sorted(event["context"]):
        tags.append("{}:{}".format(key, event["context"][key]))
    return "events.emitted:1|c|#" + ",".join(tags)
