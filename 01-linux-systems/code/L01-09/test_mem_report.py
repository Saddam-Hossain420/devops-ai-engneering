"""Tests for mem_report.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mem_report as mr  # noqa: E402


class MeminfoTest(unittest.TestCase):
    def test_sample(self) -> None:
        mi = mr.parse_meminfo((HERE / "sample-meminfo.txt").read_text(encoding="utf-8"))
        self.assertEqual(mi["Active(anon)"], 1820300)
        s = mr.memory_summary(mi)
        self.assertEqual(s["total_gib"], 7.76)
        self.assertEqual(s["available_gib"], 4.88)
        self.assertEqual(s["used_percent"], 37.1)      # (8137600-5120800)/8137600
        self.assertEqual(s["swap_used_percent"], 4.1)  # (2097148-2011132)/2097148
        self.assertIn("page cache", mr.memory_verdict(s))

    def test_verdict_levels(self) -> None:
        base = {"total_gib": 8.0, "free_gib": 0.1, "cache_gib": 0.0, "available_gib": 0.5,
                "swap_used_percent": 0.0}
        self.assertTrue(mr.memory_verdict({**base, "used_percent": 93.0}).startswith("CRITICAL"))
        self.assertTrue(mr.memory_verdict({**base, "used_percent": 85.0}).startswith("WARNING"))


class LoadTest(unittest.TestCase):
    def test_parse_and_verdict(self) -> None:
        self.assertEqual(mr.parse_loadavg("2.10 1.50 0.90 3/512 12345\n"), (2.1, 1.5, 0.9, 3, 512))
        self.assertTrue(mr.load_verdict(2.0, 1.0, 4).startswith("OK"))
        self.assertIn("বাড়ছে", mr.load_verdict(2.0, 1.0, 4))
        self.assertTrue(mr.load_verdict(7.0, 7.0, 4).startswith("OVERLOADED"))
        self.assertTrue(mr.load_verdict(5.0, 5.0, 4).startswith("BUSY"))


class PressureTest(unittest.TestCase):
    def test_psi(self) -> None:
        text = "some avg10=1.50 avg60=0.40 avg300=0.10 total=123456\nfull avg10=0.20 avg60=0.05 avg300=0.00 total=9999\n"
        p = mr.parse_pressure(text)
        self.assertEqual(p["some"]["avg10"], 1.5)
        self.assertEqual(p["full"]["total"], 9999.0)


class OomTest(unittest.TestCase):
    def test_sample_kernel_log(self) -> None:
        kills = mr.parse_oom((HERE / "sample-kernel.log").read_text(encoding="utf-8"))
        self.assertEqual(len(kills), 2)
        self.assertEqual((kills[0].comm, kills[0].pid, kills[0].anon_rss_mib, kills[0].cgroup_limit),
                         ("python3", 4821, 6656.0, False))
        self.assertEqual((kills[1].comm, kills[1].anon_rss_mib, kills[1].cgroup_limit),
                         ("taskflow-api", 256.0, True))

    def test_cli(self) -> None:
        self.assertEqual(mr.main(["oom", str(HERE / "sample-kernel.log")]), 1)
        self.assertEqual(mr.main(["meminfo", str(HERE / "sample-meminfo.txt")]), 0)
        self.assertEqual(mr.main(["meminfo", str(HERE / "nope.txt")]), 2)


if __name__ == "__main__":
    unittest.main()
