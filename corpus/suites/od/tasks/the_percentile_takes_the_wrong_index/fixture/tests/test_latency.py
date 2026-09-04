"""Visible tests.

⚠ Every window here has ten samples, so `n * p` is a whole number at both p50
and p95 and the two ways of turning it into an index cannot be told apart.
"""

from latency import percentiles


TEN = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]


def test_empty_window_is_zero():
    assert percentiles.value_at([], 0.95) == 0


def test_value_at_sorts_first():
    assert percentiles.value_at([30, 10, 20], 0.0) == 10


def test_p50_of_ten_samples():
    assert percentiles.value_at(TEN, 0.50) in (50, 60)


def test_p95_of_ten_samples_is_not_the_maximum():
    assert percentiles.value_at(TEN, 0.95) <= 100


def test_summary_reports_both():
    out = percentiles.summary(TEN)
    assert set(out) == {"p50", "p95"}
