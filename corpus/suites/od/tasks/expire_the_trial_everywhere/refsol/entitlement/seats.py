"""Seat capacity — the number finance plans against."""

from . import model


def billable_seats(accounts, as_of):
    total = 0
    for account in accounts:
        if model.is_entitled(account, as_of):
            total += account.seats
    return total
