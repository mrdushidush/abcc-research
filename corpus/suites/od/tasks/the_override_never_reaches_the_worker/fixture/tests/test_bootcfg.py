"""Visible tests.

⚠ Every override built here is written as a literal of the right type, so the
type test never rejects one. Nothing in the suite goes through `env.load`,
which is the one place overrides arrive as strings.
"""

from bootcfg import capacity, overrides, settings


def test_defaults_are_the_laptop_values():
    assert settings.DEFAULTS == {"concurrency": 1, "batch_size": 100, "timeout_s": 30}


def test_apply_lays_an_override_over_the_default():
    out = overrides.apply(settings.DEFAULTS, {"concurrency": 8})
    assert out["concurrency"] == 8
    assert out["batch_size"] == 100


def test_apply_ignores_a_key_that_is_not_a_setting():
    out = overrides.apply(settings.DEFAULTS, {"nonsense": 3})
    assert "nonsense" not in out


def test_apply_does_not_mutate_the_defaults():
    overrides.apply(settings.DEFAULTS, {"batch_size": 500})
    assert settings.DEFAULTS["batch_size"] == 100


def test_throughput_is_concurrency_times_batch():
    assert capacity.throughput({"concurrency": 8, "batch_size": 500}) == 4000


def test_check_passes_above_the_floor():
    assert capacity.check({"concurrency": 8, "batch_size": 500}) == 4000
