"""Tests for latency_experiment.py and incident_timeline.py.

চালানো: python3 -m unittest -v (এই folder থেকে)।
"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import incident_timeline as it  # noqa: E402
import latency_experiment as le  # noqa: E402


class StatsTest(unittest.TestCase):
    def test_percentile_and_summary(self) -> None:
        values = [float(x) for x in range(1, 101)]  # 1..100
        self.assertEqual(le.percentile(values, 50), 50.0)
        self.assertEqual(le.percentile(values, 95), 95.0)
        self.assertEqual(le.percentile(values, 99), 99.0)
        s = le.summarize(le.Result(values, errors=5))
        self.assertEqual(s["error_rate_percent"], 5.0)
        self.assertEqual(s["mean"], 50.5)
        self.assertEqual((s["min"], s["max"]), (1.0, 100.0))


class ServerIntegrationTest(unittest.TestCase):
    """আসল local HTTP server চালিয়ে কয়েকটি request — network-এর বাইরে যায় না।"""

    def test_work_and_flaky_endpoints(self) -> None:
        server, port = le.start_server()
        try:
            ok = le.run(port, "/work?ms=1", n=5, warmup=1)
            always_fail = le.run(port, "/flaky?ms=1&fail=100", n=5, warmup=1)
            never_fail = le.run(port, "/flaky?ms=1&fail=0", n=5, warmup=1)
        finally:
            le.stop_server(server)
        self.assertEqual((ok.total, ok.errors), (5, 0))
        self.assertEqual(always_fail.errors, 5)
        self.assertEqual(never_fail.errors, 0)
        self.assertTrue(all(ms >= 1.0 for ms in ok.latencies_ms))  # sleep অন্তত 1ms


class ParseTest(unittest.TestCase):
    def test_valid_line(self) -> None:
        e = it.parse_line('2026-10-20T14:04:00Z level=ERROR msg="db down" request_id=1')
        self.assertIsNotNone(e)
        self.assertEqual((e.level, e.msg, e.ts.minute), ("ERROR", "db down", 4))

    def test_invalid_lines(self) -> None:
        for bad in ("garbage", '2026-13-99T00:00:00Z level=ERROR msg="x"',
                    '2026-10-20T14:04:00Z level=DEBUG msg="x"'):
            self.assertIsNone(it.parse_line(bad), bad)


class TimelineTest(unittest.TestCase):
    def test_error_rate_and_window(self) -> None:
        minutes = {"10:00": Counter(INFO=9, ERROR=1), "10:01": Counter(INFO=5, ERROR=5),
                   "10:02": Counter(INFO=10)}
        self.assertEqual(it.error_rate(minutes["10:01"]), 50.0)
        self.assertEqual(it.incident_window(minutes, 20), ("10:01", "10:01"))
        self.assertIsNone(it.incident_window(minutes, 60))

    def test_sample_log(self) -> None:
        entries, skipped = it.load(HERE / "sample-app.log")
        self.assertEqual((len(entries), skipped), (120, 1))
        minutes = it.per_minute(entries)
        self.assertEqual(it.incident_window(minutes, 20), ("14:04", "14:06"))
        errors = Counter(e.msg for e in entries if e.level == "ERROR")
        self.assertEqual(errors.most_common(1)[0], ("db connection pool exhausted", 12))

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(it.main([str(HERE / "missing.log")]), 2)


if __name__ == "__main__":
    unittest.main()
