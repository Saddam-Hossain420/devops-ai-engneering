"""Tests for use_check.py and slow_app.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slow_app as sa  # noqa: E402
import use_check as uc  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_vmstat_skips_boot_average(self) -> None:
        rows = uc.parse_vmstat((HERE / "sample-vmstat.txt").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["wa"], 64)

    def test_iostat_by_column_name(self) -> None:
        io = uc.parse_iostat((HERE / "sample-iostat.txt").read_text(encoding="utf-8"))
        self.assertEqual(list(io), ["sda"])
        self.assertEqual(len(io["sda"]), 2)          # প্রথম (boot) block বাদ
        self.assertEqual(io["sda"][0]["%util"], 99.6)
        self.assertEqual(io["sda"][1]["aqu-sz"], 38.9)


class UseTableTest(unittest.TestCase):
    def test_io_bound_sample(self) -> None:
        vm = uc.parse_vmstat((HERE / "sample-vmstat.txt").read_text(encoding="utf-8"))
        io = uc.parse_iostat((HERE / "sample-iostat.txt").read_text(encoding="utf-8"))
        table = {(r[0], r[1]): (r[2], r[3]) for r in uc.use_table(vm, io, cpus=4)}
        # idle 18,15,20,16,19 → mean 17.6 → utilization 82.4% (iowait সহ)
        self.assertEqual(table[("CPU", "utilization")], ("82%", "WARN"))
        self.assertEqual(table[("CPU", "iowait")][1], "CRIT")
        self.assertEqual(table[("CPU", "saturation (run queue/cpu)")][1], "ok")
        self.assertEqual(table[("Disk sda", "utilization")], ("100%", "CRIT"))
        self.assertEqual(table[("Memory", "saturation (swap in+out)")][1], "ok")

    def test_cli(self) -> None:
        self.assertEqual(uc.main(["--vmstat", str(HERE / "sample-vmstat.txt"),
                                  "--iostat", str(HERE / "sample-iostat.txt"), "--cpus", "4"]), 1)
        self.assertEqual(uc.main(["--vmstat", str(HERE / "nope.txt"), "--cpus", "4"]), 2)


class SlowAppTest(unittest.TestCase):
    def test_slow_and_fast_agree(self) -> None:
        ids = sa.make_ids(500)
        self.assertEqual(sa.find_duplicates_slow(ids), sa.find_duplicates_fast(ids))
        self.assertEqual(sa.find_duplicates_fast([1, 2, 2, 3, 3, 3]), {2, 3})


if __name__ == "__main__":
    unittest.main()
