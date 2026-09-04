"""Bulk invite from an uploaded CSV."""

from . import limits


def invite(team, emails):
    accepted = []
    for email in emails:
        if not limits.has_room(team):
            break
        team.add_member(email)
        accepted.append(email)
    return accepted
