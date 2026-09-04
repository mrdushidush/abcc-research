"""Visible tests.

⚠ Each function is tested with a value already in the unit that function
expects, so no test composes `ingest` with `calibrate` — which is the one place
the pipeline crosses the unit boundary twice. `report.summarise` is only ever
run on a batch that is inside the bounds, so nothing pins what it does to the
readings before it looks at them.
"""

from baro import alerts, calibrate, report, units


def reading(ident, ckpa, sensor="s1"):
    return {"id": ident, "sensor": sensor, "ckpa": ckpa}


def test_to_ckpa_scales_hpa_by_ten():
    assert units.to_ckpa(1013) == 10130
    assert units.to_ckpa(0) == 0


def test_calibrate_keeps_the_ids():
    out = calibrate.apply([reading("a", 10130), reading("b", 10140)], {})
    assert [r["id"] for r in out] == ["a", "b"]


def test_bounds_are_the_instrument_range():
    assert alerts.MIN_CKPA == 9000
    assert alerts.MAX_CKPA == 11000


def test_out_of_range_splits_low_and_high():
    below, above = alerts.out_of_range(
        [reading("lo", 8000), reading("ok", 10130), reading("hi", 12000)]
    )
    assert below == ["lo"]
    assert above == ["hi"]


def test_summarise_means_a_clean_batch():
    summary = report.summarise([reading("a", 10100), reading("b", 10160)])
    assert summary["mean_ckpa"] == 10130
    assert summary["below"] == [] and summary["above"] == []


def test_summarise_means_per_sensor():
    summary = report.summarise(
        [reading("a", 10100, "s1"), reading("b", 10200, "s2"), reading("c", 10300, "s2")]
    )
    assert summary["sensor_mean"] == {"s1": 10100, "s2": 10250}
