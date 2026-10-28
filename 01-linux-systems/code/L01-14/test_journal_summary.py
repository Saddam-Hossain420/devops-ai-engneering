"""Tests for journal_summary.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import journal_summary as js  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_line(self) -> None:
        e = js.parse_line(json.dumps({"__REALTIME_TIMESTAMP": "1793005208000000", "PRIORITY": "3",
                                      "_SYSTEMD_UNIT": "x.service", "MESSAGE": "boom"}))
        self.assertEqual((e.priority, e.source, e.message), (3, "x.service", "boom"))
        self.assertEqual(e.time.year, 2026)

    def test_fallbacks(self) -> None:
        e = js.parse_line(json.dumps({"SYSLOG_IDENTIFIER": "kernel", "MESSAGE": [104, 105]}))
        self.assertEqual((e.source, e.message, e.priority), ("kernel", "hi", 6))
        self.assertIsNone(js.parse_line("{not json"))


class SummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        lines = (HERE / "sample-journal.jsonl").read_text(encoding="utf-8").splitlines()
        self.entries = [e for e in map(js.parse_line, lines) if e]

    def test_counts(self) -> None:
        self.assertEqual(len(self.entries), 121)
        s = js.summarize(self.entries, 3)
        self.assertEqual(s["worst"].priority, 2)
        self.assertIn("Out of memory", s["worst"].message)
        self.assertEqual(s["by_source"].most_common(1)[0][0], "taskflow-demo.service")
        self.assertEqual(s["selected"], sum(1 for e in self.entries if e.priority <= 3))

    def test_cli(self) -> None:
        self.assertEqual(js.main([str(HERE / "sample-journal.jsonl")]), 1)  # err/crit আছে
        self.assertEqual(js.main([str(HERE / "missing.jsonl")]), 2)


if __name__ == "__main__":
    unittest.main()
