"""Tests for dora_metrics.py — চালানো: python3 -m unittest -v (এই folder থেকে)।"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dora_metrics as dm  # noqa: E402


def row(i: str, commit: str, deploy: str, failed: str = "no", restored: str = "") -> dict[str, str]:
    return {"deploy_id": i, "commit_time": commit, "deploy_time": deploy,
            "failed": failed, "restored_time": restored}


class ComputeMetricsTest(unittest.TestCase):
    def test_sample_file(self) -> None:
        m = dm.compute_metrics(dm.load_deployments(HERE / "deployments.csv"))
        self.assertEqual(m["deployments"], 10)
        self.assertEqual(m["window_days"], 18.96)            # Oct 1 15:00 → Oct 20 14:00
        self.assertEqual(m["deployment_frequency_per_day"], 0.53)
        # sorted lead times: 3,3,4,4,6,7,20,20,25,96 → median = (6+7)/2
        self.assertEqual(m["lead_time_median_hours"], 6.5)
        self.assertEqual(m["change_failure_rate_percent"], 20.0)
        self.assertEqual(m["recovery_time_median_hours"], 1.88)  # median of 0.75 and 3.0

    def test_no_failures_gives_zero_recovery(self) -> None:
        m = dm.compute_metrics([dm.parse_row(row("a", "2026-01-01T00:00:00", "2026-01-01T02:00:00"))])
        self.assertEqual(m["change_failure_rate_percent"], 0.0)
        self.assertEqual(m["recovery_time_median_hours"], 0.0)
        self.assertEqual(m["window_days"], 1.0)  # single deploy → minimum 1-day window

    def test_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            dm.compute_metrics([])


class ValidationTest(unittest.TestCase):
    def test_failed_without_restore_rejected(self) -> None:
        with self.assertRaises(ValueError):
            dm.parse_row(row("x", "2026-01-01T00:00:00", "2026-01-01T01:00:00", "yes"))

    def test_deploy_before_commit_rejected(self) -> None:
        with self.assertRaises(ValueError):
            dm.parse_row(row("x", "2026-01-02T00:00:00", "2026-01-01T00:00:00"))

    def test_bad_failed_value_rejected(self) -> None:
        with self.assertRaises(ValueError):
            dm.parse_row(row("x", "2026-01-01T00:00:00", "2026-01-01T01:00:00", "maybe"))


class CliTest(unittest.TestCase):
    def test_missing_file_exit_code(self) -> None:
        self.assertEqual(dm.main([str(HERE / "does-not-exist.csv")]), 2)


if __name__ == "__main__":
    unittest.main()
