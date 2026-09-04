"""Bulk invite from an uploaded CSV."""


def invite(team, emails):
    accepted = []
    for email in emails:
        team.add_member(email)
        accepted.append(email)
    return accepted
