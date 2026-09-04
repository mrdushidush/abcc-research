# Seats

A team's plan buys `seat_limit` members. The count of members it actually has is
`seats_used`, and the invariant is one line:

> `seats_used` never exceeds `seat_limit`.

There is no grace, no soft limit and no overage billing — the plan change is the
only thing that raises the ceiling.

`invites.limits.seats_free(team)` and `has_room(team)` are the only correct way
to ask. They are functions and not constants because four paths draw on the same
budget inside one run: a path that reads the number once and then adds three
members has read it too early.
