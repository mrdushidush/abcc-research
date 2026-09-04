"""The console sink — what an operator watching the process sees."""

from . import redact


def render(event):
    return "{} {} {} {}".format(
        event["ts"],
        event["level"].upper(),
        redact.scrub(event["message"]),
        redact.scrub_mapping(event["context"]),
    )
