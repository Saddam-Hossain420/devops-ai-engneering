"""Tests for subnet_calc.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import subnet_calc as sc  # noqa: E402


class InfoTest(unittest.TestCase):
    def test_slash24(self) -> None:
        i = sc.info("10.0.1.0/24")
        self.assertEqual((i["netmask"], i["broadcast"], i["first_usable"], i["last_usable"], i["usable_hosts"]),
                         ("255.255.255.0", "10.0.1.255", "10.0.1.1", "10.0.1.254", 254))
        self.assertEqual(i["usable_in_aws_subnet"], 251)
        self.assertTrue(str(i["type"]).startswith("private"))

    def test_slash26_and_host_bits_set(self) -> None:
        i = sc.info("192.168.1.77/26")            # strict=False: host bit থাকলেও network বের করে
        self.assertEqual((i["network"], i["broadcast"], i["usable_hosts"], i["wildcard"]),
                         ("192.168.1.64/26", "192.168.1.127", 62, "0.0.0.63"))

    def test_small_and_special(self) -> None:
        self.assertEqual(sc.info("10.0.0.0/31")["usable_hosts"], 2)       # RFC 3021 point-to-point
        self.assertEqual(sc.info("10.0.0.5/32")["usable_hosts"], 1)
        self.assertTrue(str(sc.info("100.64.1.0/24")["type"]).startswith("shared"))
        self.assertEqual(sc.info("8.8.8.0/24")["type"], "global (public)")

    def test_ipv6(self) -> None:
        i = sc.info("2001:db8:abcd::/48")
        self.assertEqual(i["/64 subnets inside"], 65536)
        self.assertEqual(i["version"], 6)


class SplitOverlapPlanTest(unittest.TestCase):
    def test_split(self) -> None:
        subs = sc.split("10.0.0.0/16", 18)
        self.assertEqual(subs, ["10.0.0.0/18", "10.0.64.0/18", "10.0.128.0/18", "10.0.192.0/18"])
        with self.assertRaises(ValueError):
            sc.split("10.0.0.0/16", 16)

    def test_overlap(self) -> None:
        self.assertEqual(sc.overlaps(["10.0.0.0/16", "10.0.128.0/17", "192.168.0.0/16"]),
                         [("10.0.0.0/16", "10.0.128.0/17")])
        self.assertEqual(sc.overlaps(["10.0.0.0/24", "10.0.1.0/24"]), [])

    def test_plan(self) -> None:
        rows = sc.plan("10.20.0.0/16", 3, ["public", "private", "database"], 20)
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[0], ("public", "az-a", "10.20.0.0/20"))
        self.assertEqual(rows[-1], ("database", "az-c", "10.20.128.0/20"))
        self.assertEqual(sc.overlaps([r[2] for r in rows]), [])
        with self.assertRaises(ValueError):
            sc.plan("10.20.0.0/22", 3, ["public", "private"], 24)       # ৬টি দরকার, আছে ৪টি

    def test_cli(self) -> None:
        self.assertEqual(sc.main(["contains", "10.0.1.0/24", "10.0.2.1"]), 1)
        self.assertEqual(sc.main(["overlap", "10.0.0.0/8", "10.1.0.0/16"]), 1)
        self.assertEqual(sc.main(["info", "10.0.0.300/24"]), 2)


if __name__ == "__main__":
    unittest.main()
