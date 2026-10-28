"""Tests for flow_metrics.py — চালানো: python3 -m unittest -v (এই folder থেকে)।"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flow_metrics as fm  # noqa: E402


def item(i: str, started: str, done: str = "") -> fm.Item:
    return fm.parse_row({"item_id": i, "type": "x", "started": started, "done": done})


class CycleTimeTest(unittest.TestCase):
    def test_same_day_is_one_day(self) -> None:
        self.assertEqual(item("a", "2026-01-01", "2026-01-01").cycle_days, 1)

    def test_open_item_has_no_cycle(self) -> None:
        self.assertIsNone(item("a", "2026-01-01").cycle_days)

    def test_done_before_started_rejected(self) -> None:
        with self.assertRaises(ValueError):
            item("a", "2026-01-05", "2026-01-01")


class PercentileTest(unittest.TestCase):
    def test_nearest_rank(self) -> None:
        values = [1, 2, 2, 3, 3, 4, 5, 8, 9, 10, 11, 4]
        self.assertEqual(fm.percentile(values, 50), 4)   # rank 6 of 12
        self.assertEqual(fm.percentile(values, 85), 10)  # rank ceil(10.2)=11
        self.assertEqual(fm.percentile([7], 85), 7)


class WipTest(unittest.TestCase):
    def test_wip_counts_open_and_same_day(self) -> None:
        items = [item("a", "2026-01-01", "2026-01-03"), item("b", "2026-01-02")]
        self.assertEqual(fm.wip_on(items, date(2026, 1, 1)), 1)
        self.assertEqual(fm.wip_on(items, date(2026, 1, 3)), 2)
        self.assertEqual(fm.wip_on(items, date(2026, 1, 4)), 1)


class SampleTest(unittest.TestCase):
    def test_sample_file(self) -> None:
        items = fm.load_items(HERE / "work_items.csv")
        m = fm.flow_metrics(items, date(2026, 9, 1), date(2026, 9, 30))
        self.assertEqual(m["finished"], 12)
        self.assertEqual(m["period_days"], 30)
        self.assertEqual(m["throughput_per_day"], 0.4)
        # cycle days: 4,1,8,2,2,11,5,1,3,10,2,9 → sum 58
        self.assertEqual(m["cycle_time_avg_days"], 4.83)  # 58 / 12
        self.assertEqual(m["cycle_time_p50_days"], 3)     # sorted rank 6
        self.assertEqual(m["cycle_time_p85_days"], 10)    # sorted rank 11
        self.assertEqual(m["avg_wip"], 2.03)              # (58 + 3 open-days of W-13) / 30
        self.assertEqual(m["littles_law_wip"], 1.93)      # 0.4 × 4.8333

    def test_cli_errors(self) -> None:
        self.assertEqual(fm.main([str(HERE / "missing.csv")]), 2)
        self.assertEqual(fm.main([str(HERE / "work_items.csv"), "--start", "2030-01-01"]), 2)


if __name__ == "__main__":
    unittest.main()
