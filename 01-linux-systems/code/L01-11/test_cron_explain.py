"""Tests for cron_explain.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cron_explain as ce  # noqa: E402

START = datetime(2026, 10, 26, 8, 50)  # Monday


class FieldTest(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertEqual(ce.parse_field("*/15", 0, 59), {0, 15, 30, 45})
        self.assertEqual(ce.parse_field("1-5", 0, 7), {1, 2, 3, 4, 5})
        self.assertEqual(ce.parse_field("1,15,30", 0, 59), {1, 15, 30})
        self.assertEqual(ce.parse_field("5/20", 0, 59), {5, 25, 45})

    def test_invalid(self) -> None:
        for bad in ("60", "5-1", "*/0", "x"):
            with self.assertRaises(ValueError, msg=bad):
                ce.parse_field(bad, 0, 59)
        with self.assertRaises(ValueError):
            ce.Cron("* * * *")


class NextRunTest(unittest.TestCase):
    def test_business_hours_every_15(self) -> None:
        runs = ce.Cron("*/15 9-17 * * 1-5").next_runs(START, 3)
        self.assertEqual(runs, [datetime(2026, 10, 26, 9, 0), datetime(2026, 10, 26, 9, 15),
                                datetime(2026, 10, 26, 9, 30)])

    def test_friday_evening_skips_weekend(self) -> None:
        runs = ce.Cron("0 9 * * 1-5").next_runs(datetime(2026, 10, 30, 18, 0), 1)  # Friday
        self.assertEqual(runs, [datetime(2026, 11, 2, 9, 0)])  # Monday

    def test_sunday_as_7(self) -> None:
        runs = ce.Cron("30 2 * * 7").next_runs(START, 1)
        self.assertEqual(runs, [datetime(2026, 11, 1, 2, 30)])  # next Sunday

    def test_dom_dow_or_rule(self) -> None:
        # "১ তারিখে অথবা সোমবারে" — দুটোই মেলে
        runs = ce.Cron("0 0 1 * 1").next_runs(datetime(2026, 10, 27, 0, 0), 2)
        self.assertEqual(runs, [datetime(2026, 11, 1, 0, 0), datetime(2026, 11, 2, 0, 0)])

    def test_feb_30_never(self) -> None:
        self.assertEqual(ce.Cron("0 0 30 2 *").next_runs(START, 1, horizon_days=800), [])


class OnCalendarTest(unittest.TestCase):
    def test_conversions(self) -> None:
        self.assertEqual(ce.to_oncalendar("*/5 * * * *"), "*-*-* *:00/5:00")
        self.assertEqual(ce.to_oncalendar("30 2 * * 0"), "Sun *-*-* 02:30:00")
        self.assertEqual(ce.to_oncalendar("0 9 * * 1-5"), "Mon..Fri *-*-* 09:00:00")
        self.assertIn("manual", ce.to_oncalendar("0 0 1 * 1"))


if __name__ == "__main__":
    unittest.main()
