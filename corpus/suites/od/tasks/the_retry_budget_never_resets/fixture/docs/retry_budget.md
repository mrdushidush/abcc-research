# The retry budget

Three retries per hour, per window. The window is an hour of wall clock, and
**an event belongs to the window its own timestamp falls in** — not the window
the process happens to be running in. That distinction is the whole point of a
budget that resets: a replay of yesterday's failures has to spend yesterday's
budget hour by hour, exactly as the live scheduler did.

`Budget.started_at` exists so the budget can be constructed before any event has
been seen. It is not the window.

## The SLA

`retryd.report` holds the floor: at least 70% of a day's failures get a retry.

The denominator is **every failure**, deliberately. A rate computed over only
the failures we chose to retry is 100% by construction and reports nothing —
it would pass hardest exactly when the scheduler is retrying least.
