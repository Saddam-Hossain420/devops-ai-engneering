"""Tests for make_pcap.py and pcap_summary.py — চালানো: python3 -m unittest -v

pcap synthetic: make_pcap.py দিয়ে temporary file-এ তৈরি।
"""
from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import make_pcap as mk  # noqa: E402
import pcap_summary as ps  # noqa: E402


class PcapTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "t.pcap"
        mk.write_pcap(self.path, mk.scenario())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def pkts(self, path: Path | None = None) -> list[ps.Pkt]:
        lt, recs = ps.read_pcap((path or self.path).read_bytes())
        return [ps.decode(t, f, lt) for t, f in recs]

    def test_read_and_decode(self) -> None:
        pkts = self.pkts()
        self.assertEqual(len(pkts), 15)
        self.assertEqual([p.proto for p in pkts[:3]], ["UDP", "UDP", "TCP"])
        self.assertEqual((pkts[0].dport, pkts[1].sport), (53, 53))
        self.assertEqual(pkts[2].flag_str(), "S")
        self.assertEqual(pkts[3].flag_str(), "S.")
        self.assertEqual(pkts[5].flag_str(), "P.")
        self.assertEqual(pkts[5].length, 41)               # HTTP request

    def test_checksums_valid(self) -> None:
        # IP header ও TCP/UDP checksum যাচাই: সঠিক হলে পুনরায় হিসাব = 0
        _, recs = ps.read_pcap(self.path.read_bytes())
        for _, frame in recs:
            ip = frame[14:]
            self.assertEqual(mk.checksum(ip[:20]), 0)
            total, proto = struct.unpack("!H", ip[2:4])[0], ip[9]
            seg = ip[20:total]
            pseudo = ip[12:20] + struct.pack("!BBH", 0, proto, len(seg))
            self.assertEqual(mk.checksum(pseudo + seg), 0)

    def test_tcpdump_style_line(self) -> None:
        p = self.pkts()[3]
        self.assertTrue(ps.line(p).endswith(
            "IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [S.], seq 5000, ack 1001, win 65160, length 0"))

    def test_analysis(self) -> None:
        findings = ps.analyze(self.pkts())
        self.assertTrue(findings[0].startswith("handshake 10.0.0.5:51514 → 10.0.0.10:80  RTT 0.45 ms"))
        self.assertEqual(sum(f.startswith("RETRANSMISSION") for f in findings), 1)
        self.assertTrue(any(f.startswith("RST 10.0.0.10:5432") for f in findings))
        self.assertFalse(any("ZERO WINDOW" in f for f in findings))   # RST-এর window 0 গণ্য নয়

    def test_big_endian(self) -> None:
        be = Path(self.tmp.name) / "be.pcap"
        mk.write_pcap(be, mk.scenario(), big_endian=True)
        self.assertEqual(len(self.pkts(be)), 15)
        self.assertEqual(self.pkts(be)[3].seq, 5000)

    def test_errors_and_cli(self) -> None:
        bad = Path(self.tmp.name) / "bad.pcap"
        bad.write_bytes(self.path.read_bytes()[:-5])                 # কাটা file
        with self.assertRaises(ValueError):
            ps.read_pcap(bad.read_bytes())
        with self.assertRaises(ValueError):
            ps.read_pcap(b"\x0a\x0d\x0d\x0a" + b"\x00" * 30)          # pcapng magic
        self.assertEqual(ps.main([str(self.path), "--analyze-only"]), 1)
        self.assertEqual(ps.main([str(bad)]), 2)

    def test_vlan_tag(self) -> None:
        t, f = mk.scenario()[2]
        tagged = f[:12] + b"\x81\x00" + struct.pack("!H", 20) + f[12:]   # VLAN 20
        p = ps.decode(t, tagged, 1)
        self.assertEqual((p.proto, p.dport, p.flag_str()), ("TCP", 80, "S"))


if __name__ == "__main__":
    unittest.main()
