"""Visible tests.

⚠ Every cohort here has an ODD size, so the even branch — which is the whole of
the reporting standard that is interesting — is never taken.
"""

from cohort import group, stats


def test_median_of_three():
    assert stats.median([300, 100, 200]) == 200


def test_median_of_one():
    assert stats.median([7]) == 7


def test_median_of_five():
    assert stats.median([5, 1, 4, 2, 3]) == 3


def test_median_of_nothing_is_zero():
    assert stats.median([]) == 0


def test_by_region_groups_amounts():
    orders = [
        {"id": "a", "region": "north", "amount_cents": 100},
        {"id": "b", "region": "south", "amount_cents": 200},
        {"id": "c", "region": "north", "amount_cents": 300},
    ]
    assert group.by_region(orders) == {"north": [100, 300], "south": [200]}
