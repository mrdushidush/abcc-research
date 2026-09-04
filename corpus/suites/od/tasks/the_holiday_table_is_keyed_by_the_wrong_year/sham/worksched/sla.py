"""Support SLA due dates."""

import datetime

from . import businessdays, closures as closures_mod


class DueOnClosedDay(Exception):
    pass


def due(ticket):
    return businessdays.add_business_days(
        businessdays.parse(ticket["opened"]), ticket["sla_days"]
    )


def due_dates(tickets):
    # A due date must not land on a day the building is shut. Push it forward to
    # the next weekday the office is open.
    closures = closures_mod.load()
    out = []
    for ticket in tickets:
        day = due(ticket)
        while day.weekday() >= 5 or closures.closed(day):
            day = day + datetime.timedelta(days=1)
        out.append((ticket["id"], day))
    return out


def check(pairs, closures):
    """A due date on a day the building is shut is not a due date."""
    bad = [(ident, day) for ident, day in pairs if closures.closed(day)]
    if bad:
        raise DueOnClosedDay(
            "{} tickets are due on a day the office is closed; first is {} on {}".format(
                len(bad), bad[0][0], bad[0][1].isoformat()
            )
        )
    return len(pairs)
