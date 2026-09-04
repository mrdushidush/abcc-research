"""Visible tests.

⚠ Two absences, both deliberate and both realistic. Every timestamp here is
inside ONE hour, so the budget is never asked to reset — which is the behaviour
it gets wrong. And every `report` case here is one where nothing was dropped, so
the SLA denominator is never pinned by a test.
"""

from retryd import budget as budget_mod, report, scheduler

BASE = 1788004800


def failure(ident, offset):
    return {"id": ident, "ts": BASE + offset, "job": "sync-1", "error": "upstream timeout"}


def test_budget_allows_three_in_a_window():
    budget = budget_mod.Budget(BASE)
    for offset in (10, 20, 30):
        assert budget.has_room(BASE + offset) is True
        budget.spend(BASE + offset)
    assert budget.has_room(BASE + 40) is False


def test_budget_counts_one_window_when_everything_is_in_one_hour():
    budget = budget_mod.Budget(BASE)
    budget.spend(BASE + 10)
    budget.spend(BASE + 20)
    assert budget.windows_used() == 1


def test_scheduler_retries_everything_when_there_is_room():
    budget = budget_mod.Budget(BASE)
    retried, dropped = scheduler.run(budget, [failure("a", 10), failure("b", 20)])
    assert retried == ["a", "b"]
    assert dropped == []


def test_scheduler_drops_what_it_has_no_budget_for():
    budget = budget_mod.Budget(BASE)
    failures = [failure("a", 10), failure("b", 20), failure("c", 30), failure("d", 40)]
    retried, dropped = scheduler.run(budget, failures)
    assert retried == ["a", "b", "c"]
    assert dropped == ["d"]


def test_retry_rate_is_one_when_nothing_was_dropped():
    assert report.retry_rate(["a", "b", "c"], []) == 1.0
    assert report.retry_rate([], []) == 1.0


def test_check_returns_the_rate_when_everything_was_retried():
    assert report.check(["a", "b"], []) == 1.0
