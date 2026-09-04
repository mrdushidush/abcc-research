"""Support SLA due dates."""

from . import businessdays


class DueOnClosedDay(Exception):
    pass


def due(ticket):
    return businessdays.add_business_days(
        businessdays.parse(ticket["opened"]), ticket["sla_days"]
    )


def due_dates(tickets):
    return [(t["id"], due(t)) for t in tickets]


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
