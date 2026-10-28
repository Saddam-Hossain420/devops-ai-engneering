"""Tests for route_nat.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import route_nat as rn  # noqa: E402


class RouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.routes = rn.parse_routes((HERE / "sample-routes.txt").read_text(encoding="utf-8"))

    def test_parse(self) -> None:
        self.assertEqual(len(self.routes), 8)
        self.assertEqual(str(self.routes[0].dest), "0.0.0.0/0")
        self.assertEqual(self.routes[-1].kind, "blackhole")

    def test_longest_prefix_wins(self) -> None:
        self.assertEqual(rn.lookup(self.routes, "10.8.4.9").dev, "wg0")          # /24 > /16
        self.assertEqual(rn.lookup(self.routes, "10.8.9.9").via, "192.168.56.254")  # /16
        self.assertIsNone(rn.lookup(self.routes, "192.168.56.77").via)            # directly connected

    def test_metric_breaks_tie(self) -> None:
        r = rn.lookup(self.routes, "8.8.8.8")
        self.assertEqual((r.via, r.metric), ("10.0.2.2", 100))

    def test_blackhole_and_no_route(self) -> None:
        self.assertEqual(rn.lookup(self.routes, "198.51.100.5").kind, "blackhole")
        only_local = rn.parse_routes("192.168.56.0/24 dev enp0s8 proto kernel scope link\n")
        self.assertIsNone(rn.lookup(only_local, "8.8.8.8"))


class NatTest(unittest.TestCase):
    def test_translation_and_reverse(self) -> None:
        nat = rn.Nat("203.0.113.7", range(61000, 61004))
        a = nat.outbound("192.168.1.10", 51000, "93.184.215.14:443")
        b = nat.outbound("192.168.1.11", 51000, "93.184.215.14:443")   # একই private port, ভিন্ন host
        self.assertNotEqual(a, b)
        self.assertEqual(nat.outbound("192.168.1.10", 51000, "93.184.215.14:443"), a)   # একই flow → একই port
        self.assertEqual(nat.inbound(a[1], "93.184.215.14:443"), ("192.168.1.10", 51000))
        self.assertIsNone(nat.inbound(61003, "198.51.100.9:22"))                   # অযাচিত inbound drop

    def test_port_exhaustion(self) -> None:
        nat = rn.Nat("203.0.113.7", range(61000, 61002))
        nat.outbound("10.0.0.1", 1, "x:1")
        nat.outbound("10.0.0.2", 1, "x:1")
        with self.assertRaises(RuntimeError):
            nat.outbound("10.0.0.3", 1, "x:1")

    def test_cli(self) -> None:
        self.assertEqual(rn.main(["nat", "--public", "203.0.113.7", "--ports", "61000-61003",
                                  "--flows", str(HERE / "sample-flows.txt")]), 1)   # ৫টি flow, ৪টি port
        self.assertEqual(rn.main(["lookup", str(HERE / "sample-routes.txt"), "8.8.8.8"]), 0)


if __name__ == "__main__":
    unittest.main()
