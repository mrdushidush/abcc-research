"""Just-in-time provisioning on first SSO login."""


def invite(team, emails):
    accepted = []
    for email in emails:
        team.add_member(email)
        accepted.append(email)
    return accepted
