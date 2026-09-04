"""The leak canary.

Counts the secrets left in something we already rendered. It is the last check
before a payload leaves, and it is deliberately independent of `redact.scrub` —
counting with the function that was supposed to have removed them would only
prove the function agrees with itself.
"""

import re

LIVE_KEY = re.compile(r"sk_live_[A-Za-z0-9]+")


def leaks(text):
    return len(LIVE_KEY.findall(str(text)))
