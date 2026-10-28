"""Tests for storage_report.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import storage_report as sr  # noqa: E402


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


class HumanTest(unittest.TestCase):
    def test_units(self) -> None:
        self.assertEqual(sr.human(512), "512 B")
        self.assertEqual(sr.human(2147483648), "2.0 GiB")
        self.assertEqual(sr.human(53687091200), "50.0 GiB")


class LsblkTest(unittest.TestCase):
    def test_tree(self) -> None:
        lines = sr.lsblk_tree(load("sample-lsblk.json"))
        self.assertEqual(len(lines), 7)
        self.assertTrue(lines[0].startswith("sda "))
        self.assertIn("LVM2_member", lines[3])
        root_line = next(line for line in lines if line.rstrip().endswith(" /"))
        self.assertIn("ubuntu--vg-ubuntu--lv", root_line)
        self.assertIn("lvm", root_line)


class LvmTest(unittest.TestCase):
    def test_report_and_warning(self) -> None:
        lines, warns = sr.lvm_report(load("sample-vgs.json"), load("sample-lvs.json"))
        # 23566745600 / 50410291200 = 46.7499...% → 46.7
        self.assertIn("VG ubuntu-vg: size 46.9 GiB, free 21.9 GiB (46.7%)", lines)
        self.assertEqual(len(warns), 1)
        self.assertIn("data-vg", warns[0])


class ForecastTest(unittest.TestCase):
    def test_days(self) -> None:
        self.assertAlmostEqual(sr.days_until_full(50, 41, 0.6), 15.0)        # (50-41)/0.6
        self.assertAlmostEqual(sr.days_until_full(50, 41, 0.6, 0.9), 6.6667, places=3)
        self.assertEqual(sr.days_until_full(50, 41, 0.6, 0.8), 0.0)          # already above 80%
        self.assertTrue(math.isinf(sr.days_until_full(50, 10, 0)))

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            sr.days_until_full(50, 60, 1)

    def test_cli(self) -> None:
        self.assertEqual(sr.main(["lvm", str(HERE / "sample-vgs.json"), str(HERE / "sample-lvs.json")]), 1)
        self.assertEqual(sr.main(["lsblk", str(HERE / "missing.json")]), 2)


if __name__ == "__main__":
    unittest.main()
