"""POST /v1/teams/{id}/members."""


def invite(team, emails):
    accepted = []
    for email in emails:
        team.add_member(email)
        accepted.append(email)
    return accepted
