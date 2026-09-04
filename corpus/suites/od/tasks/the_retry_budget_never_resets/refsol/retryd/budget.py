"""The retry budget.

Retries are rate-limited per hour so that a bad upstream cannot turn one outage
into a self-inflicted second one. The budget is per WINDOW: three retries an
hour, and the window an event belongs to is decided by when the event happened.
"""

WINDOW_SECONDS = 3600
PER_WINDOW = 3


class Budget:
    def __init__(self, started_at):
        self.started_at = int(started_at)
        self.spent = {}

    def window_key(self, ts):
        """Which hour window `ts` falls in."""
        return int(ts) // WINDOW_SECONDS

    def has_room(self, ts):
        return self.spent.get(self.window_key(ts), 0) < PER_WINDOW

    def spend(self, ts):
        key = self.window_key(ts)
        self.spent[key] = self.spent.get(key, 0) + 1
        return key

    def windows_used(self):
        return len(self.spent)
