"""Tests for boot_report.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import boot_report as br  # noqa: E402


class DurationTest(unittest.TestCase):
    def test_formats(self) -> None:
        self.assertAlmostEqual(br.to_seconds("1min 6.401s"), 66.401)
        self.assertAlmostEqual(br.to_seconds("812ms"), 0.812)
        self.assertAlmostEqual(br.to_seconds("3.118s"), 3.118)
        self.assertAlmostEqual(br.to_seconds("2min 3s"), 123.0)
        with self.assertRaises(ValueError):
            br.to_seconds("soon")


class BootTest(unittest.TestCase):
    def test_analyze_and_blame(self) -> None:
        phases = br.parse_analyze((HERE / "sample-analyze.txt").read_text(encoding="utf-8"))
        self.assertAlmostEqual(phases["total"], 73.552)
        self.assertAlmostEqual(phases["userspace"], 66.401)
        blame = br.parse_blame((HERE / "sample-blame.txt").read_text(encoding="utf-8"))
        self.assertEqual(blame[0][1], "systemd-networkd-wait-online.service")
        self.assertEqual(len(blame), 8)

    def test_no_startup_line(self) -> None:
        with self.assertRaises(ValueError):
            br.parse_analyze("Bootup is not yet finished.")


class RebootTest(unittest.TestCase):
    def test_numeric_version_sort(self) -> None:
        kernels = br.kernel_versions((HERE / "sample-kernels.txt").read_text(encoding="utf-8"))
        self.assertEqual(kernels, ["6.8.0-9-generic", "6.8.0-45-generic", "6.8.0-48-generic"])

    def test_fedora_names(self) -> None:
        kernels = br.kernel_versions("/boot/vmlinuz-6.11.4-301.fc41.x86_64 "
                                     "/boot/vmlinuz-0-rescue-abc /boot/vmlinuz-6.11.10-300.fc41.x86_64")
        self.assertEqual(kernels[-1], "6.11.10-300.fc41.x86_64")   # 10 > 4 সংখ্যা হিসেবে
        self.assertEqual(len(kernels), 2)                           # rescue বাদ

    def test_decisions(self) -> None:
        self.assertEqual(br.reboot_needed("6.8.0-48-generic", ["6.8.0-45-generic", "6.8.0-48-generic"], []),
                         (False, []))
        needed, reasons = br.reboot_needed("6.8.0-45-generic", ["6.8.0-48-generic"], ["libc6"])
        self.assertTrue(needed)
        self.assertEqual(len(reasons), 3)

    def test_cli(self) -> None:
        args = ["reboot", "--running", str(HERE / "sample-running.txt"), "--kernels", str(HERE / "sample-kernels.txt")]
        self.assertEqual(br.main(args), 1)
        self.assertEqual(br.main(["boot", str(HERE / "x.txt"), str(HERE / "y.txt")]), 2)


if __name__ == "__main__":
    unittest.main()
