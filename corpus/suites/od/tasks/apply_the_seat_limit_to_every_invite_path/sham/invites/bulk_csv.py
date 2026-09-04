"""Bulk invite from an uploaded CSV."""

from . import limits


def invite(team, emails):
    # Do not take a CSV over the team's seat limit.
    room = limits.seats_free(team)
    accepted = []
    for email in emails[:room]:
        team.add_member(email)
        accepted.append(email)
    return accepted
