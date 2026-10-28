"""Tests for packet_layers.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import packet_layers as pl  # noqa: E402

PAYLOAD = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"


class ChecksumTest(unittest.TestCase):
    def test_rfc1071_example(self) -> None:
        # RFC 1071 section 3-এর উদাহরণ word: 0001 f203 f4f5 f6f7 → sum ddf2 → checksum 220d
        self.assertEqual(pl.checksum(bytes.fromhex("0001f203f4f5f6f7")), 0x220D)

    def test_valid_header_sums_to_zero(self) -> None:
        pkt = pl.ipv4_packet("10.0.0.1", "10.0.0.2", b"x" * 20)
        self.assertEqual(pl.checksum(pkt[:20]), 0)


class EncapsulationTest(unittest.TestCase):
    def test_sizes(self) -> None:
        frame, sizes = pl.build(PAYLOAD)
        self.assertEqual(dict(sizes), {"L7 application (HTTP)": 37, "L4 TCP header": 20,
                                       "L3 IPv4 header": 20, "L2 Ethernet header": 14})
        self.assertEqual(len(frame), 91)

    def test_round_trip(self) -> None:
        frame, _ = pl.build(PAYLOAD)
        d = pl.decode(frame)
        self.assertEqual((d.src_ip, d.dst_ip, d.src_port, d.dst_port, d.ttl), ("192.168.1.10", "93.184.215.14",
                                                                              51544, 80, 64))
        self.assertTrue(d.ip_header_ok)
        self.assertEqual(d.payload, PAYLOAD)
        self.assertEqual(d.ethertype, 0x0800)

    def test_tcp_checksum_valid_with_pseudo_header(self) -> None:
        seg = pl.tcp_segment(1234, 80, 1, b"hi", "10.0.0.1", "10.0.0.2")
        pseudo = pl.ip_bytes("10.0.0.1") + pl.ip_bytes("10.0.0.2") + struct.pack("!BBH", 0, 6, len(seg))
        self.assertEqual(pl.checksum(pseudo + seg), 0)

    def test_corruption_detected(self) -> None:
        frame = bytearray(pl.build(PAYLOAD)[0])
        frame[14 + 8] = 1          # TTL বদলানো, checksum পুরোনো
        self.assertFalse(pl.decode(bytes(frame)).ip_header_ok)


if __name__ == "__main__":
    unittest.main()
