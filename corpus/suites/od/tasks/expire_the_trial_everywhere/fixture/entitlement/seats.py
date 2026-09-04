"""Seat capacity — the number finance plans against."""

from . import model


def billable_seats(accounts, as_of):
    total = 0
    for account in accounts:
        if account.status in model.ENTITLED_STATUSES:
            total += account.seats
    return total
