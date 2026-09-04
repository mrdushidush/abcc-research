"""Visible tests.

⚠ Every team built here has room to spare, so no path in this suite is ever
asked what it does at the ceiling. That is the one question the package gets
wrong on three of its four paths.
"""

from invites import api, bulk_csv, direct, limits, sso, team as team_mod


def team(limit=100, used=0):
    return team_mod.Team({"id": "t", "seat_limit": limit, "seats_used": used})


def test_seats_free_never_goes_negative():
    assert limits.seats_free(team(10, 3)) == 7
    assert limits.seats_free(team(10, 10)) == 0
    assert limits.seats_free(team(10, 12)) == 0


def test_has_room_is_seats_free_as_a_predicate():
    assert limits.has_room(team(10, 9)) is True
    assert limits.has_room(team(10, 10)) is False


def test_direct_invite_adds_members():
    t = team()
    assert direct.invite(t, ["a@x", "b@x"]) == ["a@x", "b@x"]
    assert t.seats_used == 2


def test_bulk_invite_adds_members():
    t = team()
    assert len(bulk_csv.invite(t, ["a@x", "b@x", "c@x"])) == 3
    assert t.seats_used == 3


def test_sso_invite_adds_one_member():
    t = team()
    assert sso.invite(t, ["a@x"]) == ["a@x"]
    assert t.seats_used == 1


def test_api_invite_adds_members():
    t = team()
    assert len(api.invite(t, ["a@x", "b@x"])) == 2
    assert t.seats_used == 2
