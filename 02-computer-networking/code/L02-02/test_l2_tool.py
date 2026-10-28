"""Tests for l2_tool.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import l2_tool as lt  # noqa: E402


class MacTest(unittest.TestCase):
    def test_normalize_formats(self) -> None:
        for raw in ("52-54-00-AB-CD-EF", "5254.00ab.cdef", "52:54:00:ab:cd:ef", "525400ABCDEF"):
            self.assertEqual(lt.normalize_mac(raw), "52:54:00:ab:cd:ef")
        for bad in ("52:54:00:ab:cd", "zz:54:00:ab:cd:ef", "52:54:00:ab:cd:ef:01"):
            with self.assertRaises(ValueError, msg=bad):
                lt.normalize_mac(bad)

    def test_bits(self) -> None:
        self.assertTrue(lt.mac_info("ff:ff:ff:ff:ff:ff")["broadcast"])
        self.assertTrue(lt.mac_info("01:00:5e:00:00:fb")["multicast"])        # IPv4 multicast (mDNS)
        self.assertFalse(lt.mac_info("08:00:27:5e:1a:c3")["locally_administered"])
        self.assertTrue(lt.mac_info("52:54:00:ab:cd:ef")["locally_administered"])   # 0x52 = 0101 0010
        self.assertTrue(lt.mac_info("02:42:ac:11:00:02")["locally_administered"])   # Docker-এর MAC


class NeighTest(unittest.TestCase):
    def test_parse_and_audit(self) -> None:
        neigh = lt.parse_neigh((HERE / "sample-neigh.txt").read_text(encoding="utf-8"))
        self.assertEqual(len(neigh), 6)
        self.assertIsNone(neigh[2].mac)
        self.assertEqual(neigh[3].state, "REACHABLE")          # "router" flag সহ লাইন
        warns = lt.audit_neigh(neigh)
        self.assertEqual(len(warns), 2)
        self.assertTrue(any("192.168.56.30" in w and "FAILED" in w for w in warns))
        self.assertTrue(any("52:55:0a:00:02:02 claims 2" in w for w in warns))   # IPv6 গোনা হয় না


class VlanTest(unittest.TestCase):
    def test_encode_decode(self) -> None:
        tag = lt.vlan_tag(20, pcp=5)
        self.assertEqual(tag.hex(), "8100a014")                # 101 0 000000010100
        self.assertEqual(lt.decode_vlan(tag), {"pcp": 5, "dei": 0, "vid": 20})
        self.assertEqual(lt.decode_vlan(lt.vlan_tag(4094, 7)), {"pcp": 7, "dei": 0, "vid": 4094})

    def test_invalid(self) -> None:
        for vid in (0, 4095, 5000):
            with self.assertRaises(ValueError):
                lt.vlan_tag(vid)
        with self.assertRaises(ValueError):
            lt.decode_vlan(bytes.fromhex("88a8a014"))           # 802.1ad TPID, 802.1Q নয়

    def test_cli(self) -> None:
        self.assertEqual(lt.main(["neigh", str(HERE / "sample-neigh.txt")]), 1)
        self.assertEqual(lt.main(["mac", "nope"]), 2)


if __name__ == "__main__":
    unittest.main()
