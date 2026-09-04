"""Replay the pending invite queue against the team.

    python run.py

The line shapes are read by the provisioning audit. They are a contract.
"""

import sys

from invites import api, bulk_csv, direct, sso, team as team_mod

DATA = "data/pending.json"


def main(argv):
    raw = team_mod.load(DATA)
    team = team_mod.Team(raw["team"])

    print("INVITE RUN")
    print("team: {}".format(team.id))
    print("seat_limit: {}".format(team.seat_limit))
    print("accepted_direct: {}".format(len(direct.invite(team, raw["direct"]))))
    print("accepted_bulk: {}".format(len(bulk_csv.invite(team, raw["bulk"]))))
    print("accepted_sso: {}".format(len(sso.invite(team, raw["sso"]))))
    print("accepted_api: {}".format(len(api.invite(team, raw["api"]))))
    print("seats_used: {}".format(team.seats_used))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
