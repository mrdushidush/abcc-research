"""The scrubber.

One pattern, one function. Secrets in this system are API keys — `sk_live_`
followed by an opaque tail — and they turn up in message text, in bearer
headers and in context values, because callers put them there.
"""

import re

SECRET = re.compile(r"sk_live_[A-Za-z0-9]+")
PLACEHOLDER = "[redacted]"


def scrub(text):
    """Replace every secret in `text` with the placeholder."""
    return SECRET.sub(PLACEHOLDER, str(text))


def scrub_mapping(mapping):
    return {key: scrub(value) for key, value in mapping.items()}
