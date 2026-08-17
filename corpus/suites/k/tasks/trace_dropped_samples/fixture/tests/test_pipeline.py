"""Unit tests for the roll-up.

Run with:  python3 -m unittest discover -s tests

These cover the stages in isolation. Note what is NOT covered: there is no
end-to-end test that runs a mixed-firmware sample file all the way through
`run.py` and asserts the totals. That gap is why a whole firmware revision can
go missing without a single test turning red.
"""

import unittest

from pipeline import alerts, config, constants, normalize, stats, validate, windowing


class TestNormalize(unittest.TestCase):
    def test_canonical_flag_folds_case(self):
        self.assertEqual(normalize.canonical_flag("OK"), "ok")
        self.assertEqual(normalize.canonical_flag("  WARN "), "warn")
        self.assertEqual(normalize.canonical_flag(None), "")

    def test_canonical_channel_maps_legacy_vibration(self):
        self.assertEqual(normalize.canonical_channel("vib_mm_s"), "vibration_mm_s")
        self.assertEqual(normalize.canonical_channel("TEMP_C"), "temp_c")

    def test_canonical_record_resolves_rev_b_aliases(self):
        rec = normalize.canonical_record(
            {"ts_ms": 10, "chan": "temp_c", "val": 1.5, "quality": "OK", "dev_id": "d"}
        )
        self.assertIn(constants.TIMESTAMP_KEY, rec)
        self.assertIn(constants.VALUE_KEY, rec)
        self.assertIn(constants.FLAG_KEY, rec)
        # NOTE: canonical_record resolves NAMES only. It does not fold the
        # flag's case -- that is canonical_flag's job, and callers must do both.
        self.assertEqual(rec[constants.FLAG_KEY], "OK")


class TestValidate(unittest.TestCase):
    def test_in_bounds(self):
        self.assertTrue(validate.in_bounds("temp_c", 20.0))
        self.assertFalse(validate.in_bounds("temp_c", 999.0))
        self.assertFalse(validate.in_bounds("nope", 1.0))

    def test_clamp(self):
        self.assertEqual(validate.clamp("temp_c", 999.0), 150.0)
        self.assertEqual(validate.clamp("temp_c", 20.0), 20.0)


class TestWindowing(unittest.TestCase):
    def test_window_start_floors(self):
        self.assertEqual(windowing.window_start(0, 10_000), 0)
        self.assertEqual(windowing.window_start(9_999, 10_000), 0)
        self.assertEqual(windowing.window_start(10_001, 10_000), 10_000)


class TestStats(unittest.TestCase):
    def test_summarise_computes_mean(self):
        settings = config.load()
        w = windowing.Window("temp_c", 0, 10_000)
        for value in (10.0, 20.0, 30.0):
            w.add(
                {
                    constants.VALUE_KEY: value,
                    constants.DEVICE_KEY: "dev-a1",
                    constants.FLAG_KEY: "ok",
                }
            )
        summary = stats.summarise([w], settings)
        self.assertEqual(summary.total_samples, 3)
        self.assertAlmostEqual(summary.windows[0].mean, 20.0)


class TestAlerts(unittest.TestCase):
    def test_empty_window_raises_nothing(self):
        stat = stats.WindowStat("temp_c", 0, 0, 0.0, None, 0)
        self.assertIsNone(alerts.evaluate_window(stat))

    def test_highest_severity_wins(self):
        stat = stats.WindowStat("temp_c", 0, 5, 130.0, 130.0, 0)
        alert = alerts.evaluate_window(stat)
        self.assertIsNotNone(alert)
        self.assertEqual(alert.severity, "critical")


if __name__ == "__main__":
    unittest.main()
