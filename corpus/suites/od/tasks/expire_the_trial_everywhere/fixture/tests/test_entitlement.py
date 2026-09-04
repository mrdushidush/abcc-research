"""Visible tests.

⚠ They are happy-path on purpose: the accounts built here are active, cancelled
and suspended, plus one trial that is still running. No test puts an account
whose trial has ENDED through a consumer, which is how a whole class of account
stays wrong while the suite stays green.
"""

from entitlement import access, calendar, digest, model, seats, support

AS_OF = "2026-09-01"


def account(status, seats_n=1, ends=None, ident="ac-x"):
    return model.Account(
        {"id": ident, "name": "n", "status": status, "seats": seats_n, "trial_ends_on": ends}
    )


def test_lapsed_is_exclusive_of_the_last_day():
    assert calendar.lapsed("2026-08-31", AS_OF) is True
    assert calendar.lapsed("2026-09-01", AS_OF) is False
    assert calendar.lapsed("2026-09-02", AS_OF) is False
    assert calendar.lapsed(None, AS_OF) is False


def test_active_account_gets_premium():
    assert access.features(account("active"), AS_OF) == access.PREMIUM_FEATURES


def test_cancelled_and_suspended_get_basic():
    assert access.features(account("cancelled"), AS_OF) == access.BASIC_FEATURES
    assert access.features(account("suspended"), AS_OF) == access.BASIC_FEATURES


def test_digest_skips_cancelled_and_suspended():
    accounts = [
        account("active", ident="a"),
        account("cancelled", ident="b"),
        account("suspended", ident="c"),
    ]
    assert digest.recipients(accounts, AS_OF) == ["a"]


def test_seats_sum_over_active_accounts():
    accounts = [account("active", 3), account("active", 4), account("cancelled", 100)]
    assert seats.billable_seats(accounts, AS_OF) == 7


def test_priority_needs_five_seats():
    assert support.queue(account("active", 5), AS_OF) == support.PRIORITY
    assert support.queue(account("active", 4), AS_OF) == support.STANDARD
    assert support.queue(account("cancelled", 50), AS_OF) == support.STANDARD


def test_a_running_trial_is_still_entitled():
    live = account("trial", 8, ends="2026-09-20")
    assert access.features(live, AS_OF) == access.PREMIUM_FEATURES
    assert digest.recipients([live], AS_OF) == ["ac-x"]
    assert seats.billable_seats([live], AS_OF) == 8
