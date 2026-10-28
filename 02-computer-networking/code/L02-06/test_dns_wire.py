"""Tests for dns_wire.py — চালানো: python3 -m unittest -v

Network ছাড়া: response হাতে তৈরি, এবং একটি fake DNS server 127.0.0.1-এ চালিয়ে end-to-end।
"""
from __future__ import annotations

import socket
import struct
import sys
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dns_wire as dw  # noqa: E402


def fake_answer(query: bytes) -> bytes:
    """Query-র question হুবহু ফেরত + দুটি answer: CNAME (pointer সহ) ও A।"""
    qid = struct.unpack("!H", query[:2])[0]
    question = query[12:]
    header = struct.pack("!HHHHHH", qid, 0x8180, 1, 2, 0, 0)        # QR, RD, RA, NOERROR
    # answer 1: name = pointer to offset 12 (question name), CNAME → "web.example.net"
    cname_rdata = dw.encode_name("web.example.net")
    ans1 = b"\xc0\x0c" + struct.pack("!HHIH", 5, 1, 300, len(cname_rdata)) + cname_rdata
    # answer 2: name = pointer to the CNAME target inside answer 1's rdata
    target_offset = 12 + len(question) + 2 + 10
    ans2 = struct.pack("!H", 0xC000 | target_offset) + struct.pack("!HHIH", 1, 1, 60, 4) + bytes([203, 0, 113, 10])
    return header + question + ans1 + ans2


class WireTest(unittest.TestCase):
    def test_encode_name(self) -> None:
        self.assertEqual(dw.encode_name("www.example.com"), b"\x03www\x07example\x03com\x00")
        with self.assertRaises(ValueError):
            dw.encode_name("a" * 64 + ".com")

    def test_build_query_bytes(self) -> None:
        q = dw.build_query("example.com", "A", qid=0x1234)
        self.assertEqual(q.hex(), "123401000001000000000000076578616d706c6503636f6d0000010001")

    def test_parse_with_compression(self) -> None:
        q = dw.build_query("www.example.com", "A", qid=7)
        r = dw.parse_response(fake_answer(q))
        self.assertEqual((r.qid, r.rcode, r.recursion_available, r.question), (7, "NOERROR", True, "www.example.com"))
        self.assertEqual([(a.name, a.rtype, a.ttl, a.value) for a in r.answers],
                         [("www.example.com", "CNAME", 300, "web.example.net"),
                          ("web.example.net", "A", 60, "203.0.113.10")])

    def test_nxdomain(self) -> None:
        msg = struct.pack("!HHHHHH", 9, 0x8183, 0, 0, 0, 0)
        self.assertEqual(dw.parse_response(msg).rcode, "NXDOMAIN")

    def test_pointer_loop_rejected(self) -> None:
        msg = b"\x00" * 12 + b"\xc0\x0c"                 # নিজের দিকেই pointer
        with self.assertRaises(ValueError):
            dw.read_name(msg, 12)


class EndToEndTest(unittest.TestCase):
    def test_query_against_fake_server(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]

        def serve() -> None:
            data, addr = srv.recvfrom(512)
            srv.sendto(fake_answer(data), addr)

        t = threading.Thread(target=serve, daemon=True)
        t.start()
        try:
            r = dw.query("www.example.com", "A", "127.0.0.1", port)
        finally:
            t.join(2)
            srv.close()
        self.assertEqual(r.answers[-1].value, "203.0.113.10")

    def test_resolv_conf(self) -> None:
        p = HERE / "_resolv_test.conf"
        p.write_text("# comment\nsearch lan\nnameserver 127.0.0.53\noptions edns0\n", encoding="utf-8")
        try:
            self.assertEqual(dw.system_nameserver(p), "127.0.0.53")
        finally:
            p.unlink()


if __name__ == "__main__":
    unittest.main()
