"""Tests for http_raw.py — চালানো: python3 -m unittest -v

সব test loopback-এ local server দিয়ে (বাইরের network নয়)।
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import http_raw as hr  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_build_request(self) -> None:
        raw = hr.build_request("POST", "api.local", "/x", {"Accept": "*/*"}, b"ab", keep_alive=False)
        self.assertEqual(raw, b"POST /x HTTP/1.1\r\nHost: api.local\r\nUser-Agent: http_raw/1.0\r\n"
                              b"Connection: close\r\nAccept: */*\r\nContent-Length: 2\r\n\r\nab")

    def test_parse_head_case_insensitive(self) -> None:
        r = hr.parse_head(b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nX-A: 1")
        self.assertEqual((r.status, r.reason, r.header("content-type")), (404, "Not Found", "text/plain"))
        with self.assertRaises(ValueError):
            hr.parse_head(b"garbage")

    def test_decode_chunked(self) -> None:
        data = b"4\r\nWiki\r\n6;ext=1\r\npedia \r\nE\r\nin \r\n\r\nchunks.\r\n0\r\n\r\nNEXT"
        body, used = hr.decode_chunked(data)
        self.assertEqual(body, b"Wikipedia in \r\n\r\nchunks.")
        self.assertEqual(data[used:], b"NEXT")             # পরের response-এর byte অক্ষত
        with self.assertRaises(ValueError):
            hr.decode_chunked(b"4\r\nWi")


class LiveLocalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.srv, self.port = hr.start_server()
        self.conn = hr.Connection("127.0.0.1", self.port)

    def tearDown(self) -> None:
        self.conn.close()
        hr.stop_server(self.srv)

    def req(self, method: str, path: str, body: bytes = b"") -> hr.Response:
        return self.conn.request(hr.build_request(method, "t", path, body=body), method)

    def test_keep_alive_multiple_requests(self) -> None:
        local_port = self.conn.sock.getsockname()[1]
        self.assertEqual(self.req("GET", "/hello").body, b"hello\n")
        chunked = self.req("GET", "/chunked")
        self.assertEqual(chunked.header("Transfer-Encoding"), "chunked")
        self.assertEqual(chunked.body, b"line 1\nline 2\ndone\n")
        self.assertEqual(self.req("POST", "/hello", b"12345").body, b"got 5 bytes\n")
        self.assertEqual(self.conn.sock.getsockname()[1], local_port)   # একই TCP connection

    def test_redirect_and_404(self) -> None:
        r = self.req("GET", "/old")
        self.assertEqual((r.status, r.header("Location")), (301, "/hello"))
        self.assertEqual(self.req("GET", "/nope").status, 404)

    def test_head_has_no_body(self) -> None:
        # DemoHandler-এ do_HEAD নেই → 501; তবু body পড়ার চেষ্টা করা যাবে না
        r = self.req("HEAD", "/hello")
        self.assertEqual(r.status, 501)
        self.assertEqual(r.body, b"")

    def test_cli_get(self) -> None:
        self.assertEqual(hr.main(["get", f"http://127.0.0.1:{self.port}/hello"]), 0)
        self.assertEqual(hr.main(["get", f"http://127.0.0.1:{self.port}/nope"]), 1)
        self.assertEqual(hr.main(["get", "https://example.com/"]), 2)


if __name__ == "__main__":
    unittest.main()
