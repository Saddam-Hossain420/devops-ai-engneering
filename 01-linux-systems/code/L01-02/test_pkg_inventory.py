"""Tests for pkg_inventory.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pkg_inventory as pi  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_dpkg_and_rpm_units(self) -> None:
        d = pi.parse_inventory("nginx\t1.24.0-2ubuntu7.1\t1290\n", "dpkg")
        self.assertEqual(d["nginx"].size_kib, 1290)
        r = pi.parse_inventory("nginx\t1.26.2-1.fc41\t1890104\n", "rpm")
        self.assertEqual(r["nginx"].size_kib, 1846)  # 1890104 / 1024 ≈ 1845.8

    def test_empty_size_and_bad_line(self) -> None:
        self.assertEqual(pi.parse_inventory("meta\t1.0\t\n")["meta"].size_kib, 0)
        with self.assertRaises(ValueError):
            pi.parse_inventory("only two\tfields\n")
        with self.assertRaises(ValueError):
            pi.parse_inventory("x\t1\t1\n", "apk")


class AnalysisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.a = pi.load(HERE / "server-a.tsv", "dpkg")
        self.b = pi.load(HERE / "server-b.tsv", "dpkg")

    def test_top(self) -> None:
        top = pi.top_packages(self.a, 2)
        self.assertEqual([p.name for p in top], ["snapd", "linux-modules-6.8.0-45-generic"])

    def test_diff(self) -> None:
        only_a, only_b, changed = pi.diff_inventories(self.a, self.b)
        self.assertEqual(only_a, ["nginx"])
        self.assertEqual(only_b, ["telnetd"])
        self.assertEqual(changed, [("curl", "8.5.0-2ubuntu10.4", "8.5.0-2ubuntu10.1"),
                                   ("openssl", "3.0.13-0ubuntu3.4", "3.0.13-0ubuntu3.1")])

    def test_cli_exit_codes(self) -> None:
        a, b = str(HERE / "server-a.tsv"), str(HERE / "server-b.tsv")
        self.assertEqual(pi.main(["diff", a, b]), 1)   # drift
        self.assertEqual(pi.main(["diff", a, a]), 0)   # no drift
        self.assertEqual(pi.main(["top", str(HERE / "missing.tsv")]), 2)
        self.assertEqual(pi.main(["--format", "rpm", "top", str(HERE / "server-f.tsv"), "--n", "3"]), 0)


if __name__ == "__main__":
    unittest.main()
