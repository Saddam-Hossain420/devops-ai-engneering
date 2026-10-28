"""Tests for mtu_calc.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mtu_calc as mc  # noqa: E402


class MtuTest(unittest.TestCase):
    def test_mss_and_ping(self) -> None:
        self.assertEqual(mc.mss(1500), 1460)
        self.assertEqual(mc.mss(1500, "ipv6"), 1440)
        self.assertEqual(mc.mss(1500, tcp_options=mc.TCP_TIMESTAMPS), 1448)
        self.assertEqual(mc.max_ping_payload(1500), 1472)
        self.assertEqual(mc.max_ping_payload(9001), 8973)       # AWS jumbo frame

    def test_tunnels(self) -> None:
        self.assertEqual(mc.inner_mtu(1500, ["vxlan"]), 1450)
        self.assertEqual(mc.inner_mtu(1500, ["wireguard6"]), 1420)   # WireGuard-এর default
        self.assertEqual(mc.inner_mtu(1500, ["vxlan", "wireguard4"]), 1390)
        with self.assertRaises(ValueError):
            mc.inner_mtu(1500, ["nope"])

    def test_fragments(self) -> None:
        frs = mc.fragments(3008, 1500)                          # ping -s 3000
        self.assertEqual(frs, [(0, 1480, True), (1480, 1480, True), (2960, 48, False)])
        self.assertTrue(all(n % 8 == 0 for _, n, more in frs if more))
        self.assertEqual(mc.fragments(1480, 1500), [(0, 1480, False)])

    def test_fragment_alignment(self) -> None:
        # MTU 1006 → 986 byte জায়গা, কিন্তু ৮-এর গুণিতক 984
        self.assertEqual(mc.fragments(2000, 1006)[0], (0, 984, True))

    def test_pmtud(self) -> None:
        hops = [1500, 1500, 1400, 1500]
        found, probes = mc.pmtud_search(lambda s: s <= mc.path_mtu(hops))
        self.assertEqual(found, 1400)
        self.assertLess(probes, 16)                              # log2(8424) ≈ 13
        with self.assertRaises(ValueError):
            mc.pmtud_search(lambda s: False)                     # সব ICMP block

    def test_lease(self) -> None:
        self.assertEqual(mc.lease_timers(86400), (43200, 75600))

    def test_cli(self) -> None:
        self.assertEqual(mc.main(["tunnel", "--mtu", "9001", "vxlan"]), 0)
        self.assertEqual(mc.main(["tunnel", "bogus"]), 2)
        self.assertEqual(mc.main(["fragment", "--size", "3000"]), 0)


if __name__ == "__main__":
    unittest.main()
