"""The error tracker sink — errors only, with the full context attached."""


def render(event):
    if event["level"] != "error":
        return None
    lines = ["title: " + event["message"]]
    for key in sorted(event["context"]):
        lines.append("{}: {}".format(key, event["context"][key]))
    return "\n".join(lines)
