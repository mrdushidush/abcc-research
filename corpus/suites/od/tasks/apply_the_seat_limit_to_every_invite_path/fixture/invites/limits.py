"""The seat limit.

`seats_free` is the only correct way to ask how many more members a team may
take. It is a function rather than a constant because `seats_used` moves while
a run is in flight — four paths draw on the same budget.
"""


class SeatLimitReached(Exception):
    pass


def seats_free(team):
    return max(0, team.seat_limit - team.seats_used)


def has_room(team):
    return seats_free(team) > 0
