"""Tests for port_forward.py and wg_lint.py — চালানো: python3 -m unittest -v

Forwarder test আসল loopback connection ব্যবহার করে। WireGuard key সব synthetic।
"""
from __future__ import annotations

import socket
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import port_forward as pf  # noqa: E402
import wg_lint as wl  # noqa: E402

K1 = "EBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8="
K2 = "ICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj8="


class ForwarderTest(unittest.TestCase):
    def test_forward_and_count(self) -> None:
        srv, eport, stop = pf.echo_server()
        fw = pf.Forwarder(("127.0.0.1", 0), ("127.0.0.1", eport)).start()
        try:
            self.assertEqual(pf.roundtrip(fw.port, b"abc" * 50_000), b"ABC" * 50_000)
            self.assertEqual(pf.roundtrip(fw.port, b"second"), b"SECOND")
            time.sleep(0.1)
            self.assertEqual(fw.stats["connections"], 2)
            self.assertEqual(fw.stats["bytes_up"], 150_006)
            self.assertEqual(fw.stats["bytes_down"], 150_006)
        finally:
            fw.stop()
            stop.set()
            srv.close()

    def test_target_down_closes_client(self) -> None:
        dead = socket.socket()
        dead.bind(("127.0.0.1", 0))
        port = dead.getsockname()[1]
        dead.close()                                    # এখন এই port-এ কেউ নেই
        fw = pf.Forwarder(("127.0.0.1", 0), ("127.0.0.1", port)).start()
        try:
            with socket.create_connection(("127.0.0.1", fw.port), timeout=3) as s:
                try:
                    data = s.recv(10)                   # forwarder target-এ পৌঁছাতে না পেরে বন্ধ করে
                except ConnectionResetError:
                    data = b""
            self.assertEqual(data, b"")
            time.sleep(0.1)
            self.assertEqual(fw.stats["failed"], 1)
        finally:
            fw.stop()

    def test_split_hostport(self) -> None:
        self.assertEqual(pf.split_hostport("10.0.0.5:5432"), ("10.0.0.5", 5432))
        self.assertEqual(pf.split_hostport(":9000"), ("127.0.0.1", 9000))
        with self.assertRaises(ValueError):
            pf.split_hostport("nohost")


class WgLintTest(unittest.TestCase):
    def test_sample_findings(self) -> None:
        sections = wl.parse((HERE / "sample-wg0.conf").read_text(encoding="utf-8"))
        text = "\n".join(wl.lint(sections))
        self.assertIn("MTU 1500 > 1420", text)
        self.assertIn("10.20.5.0/24 overlaps 10.20.0.0/16", text)
        self.assertIn("no PersistentKeepalive", text)
        self.assertNotIn(K1, text)                       # private key কখনো output-এ নয়
        self.assertEqual(wl.main([str(HERE / "sample-wg0.conf")]), 1)

    def test_key_validation(self) -> None:
        self.assertTrue(wl.valid_key(K1))
        self.assertFalse(wl.valid_key("not-a-key"))
        self.assertFalse(wl.valid_key("AAAA"))           # বৈধ base64 কিন্তু ৩২ byte নয়

    def test_clean_client_config(self) -> None:
        cfg = (f"[Interface]\nAddress = 10.8.0.2/32\nPrivateKey = {K1}\n"
               f"[Peer]\nPublicKey = {K2}\nAllowedIPs = 0.0.0.0/0, ::/0\n"
               "Endpoint = vpn.example.com:51820\nPersistentKeepalive = 25\n")
        findings = wl.lint(wl.parse(cfg))
        self.assertTrue(all(f.startswith("INFO") for f in findings), findings)
        self.assertTrue(any("full tunnel" in f for f in findings))

    def test_parse_errors(self) -> None:
        for bad in ("Address = 1.2.3.4", "[Interface]\nnonsense", "[Peer]\nPublicKey = x", "[Wat]\n"):
            with self.assertRaises(ValueError, msg=bad):
                wl.parse(bad)


if __name__ == "__main__":
    unittest.main()
