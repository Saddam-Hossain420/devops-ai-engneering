"""Tests for sock_demo.py and ss_summary.py — চালানো: python3 -m unittest -v

Socket test আসল loopback connection ব্যবহার করে (বাইরের network নয়)।
"""
from __future__ import annotations

import errno
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sock_demo as sd  # noqa: E402
import ss_summary as ss  # noqa: E402


class SocketTest(unittest.TestCase):
    def test_tcp_echo(self) -> None:
        srv, port, _ = sd.tcp_echo_server()
        try:
            self.assertEqual(sd.tcp_roundtrip(port, b"abc" * 3000), b"ABC" * 3000)   # একাধিক recv চক্র
        finally:
            srv.close()

    def test_udp_echo(self) -> None:
        self.assertEqual(sd.udp_roundtrip(b"ping"), b"PING")

    def test_refused(self) -> None:
        msg = sd.connect_refused(sd.closed_port())
        self.assertIn("ConnectionRefusedError", msg)
        self.assertTrue(f"errno={errno.ECONNREFUSED}" in msg or "errno=10061" in msg)  # Linux 111 / Windows 10061

    def test_latency_samples(self) -> None:
        srv, port, _ = sd.tcp_echo_server()
        try:
            times = sd.connect_latency(port, 5)
        finally:
            srv.close()
        self.assertEqual(len(times), 5)
        self.assertTrue(all(t > 0 for t in times))


class SsTest(unittest.TestCase):
    def test_sample(self) -> None:
        rows = ss.parse_ss((HERE / "sample-ss.txt").read_text(encoding="utf-8"))
        states, listening, warns = ss.summarize(rows, 50, 5000)
        self.assertEqual(states["CLOSE-WAIT"], 62)
        self.assertEqual(states["TIME-WAIT"], 120)
        self.assertEqual(listening, ["22", "80", "8000"])          # IPv4/IPv6-এর 22 একবার
        self.assertEqual(len(warns), 2)                            # CLOSE-WAIT ও SYN-SENT; TIME-WAIT সীমার নিচে

    def test_addr_split(self) -> None:
        self.assertEqual(ss.split_addr("[::1]:22"), ("::1", "22"))
        self.assertEqual(ss.split_addr("10.0.0.5:443"), ("10.0.0.5", "443"))

    def test_cli(self) -> None:
        self.assertEqual(ss.main([str(HERE / "sample-ss.txt")]), 1)
        self.assertEqual(ss.main([str(HERE / "sample-ss.txt"), "--close-wait-warn", "100"]), 1)  # SYN-SENT এখনো


if __name__ == "__main__":
    unittest.main()
