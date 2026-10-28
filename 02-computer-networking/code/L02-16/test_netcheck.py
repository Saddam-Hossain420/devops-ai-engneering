"""Tests for netcheck.py — চালানো: python3 -m unittest -v

সব test loopback-এ local HTTP server দিয়ে; DNS failure-এর জন্য RFC 6761-এর `.invalid` নাম।
"""
from __future__ import annotations

import errno
import json
import io
import socket
import sys
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import netcheck as nc  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:
        code = 503 if self.path == "/broken" else 200
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()


class NetcheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_all_layers_pass(self) -> None:
        r = nc.check(f"http://127.0.0.1:{self.port}/health")
        self.assertTrue(r.ok)
        self.assertEqual([s.layer for s in r.steps], ["dns", "tcp", "http"])
        self.assertIn("200", r.steps[-1].detail)

    def test_http_5xx_fails(self) -> None:
        r = nc.check(f"http://127.0.0.1:{self.port}/broken")
        self.assertFalse(r.ok)
        self.assertEqual(r.steps[-1].layer, "http")
        self.assertIn("curl -v", r.hint)

    def test_refused(self) -> None:
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead = s.getsockname()[1]
        s.close()
        r = nc.check(f"http://127.0.0.1:{dead}/", timeout=5)
        self.assertEqual((r.steps[-1].layer, r.steps[-1].ok), ("tcp", False))
        self.assertIn("ss -ltnp", r.hint)

    def test_tls_against_plain_http(self) -> None:
        r = nc.check(f"https://127.0.0.1:{self.port}/")     # plain HTTP port-এ TLS handshake
        self.assertEqual((r.steps[-1].layer, r.steps[-1].ok), ("tls", False))
        self.assertIn("openssl s_client", r.hint)

    def test_dns_failure(self) -> None:
        r = nc.check("http://does-not-exist.invalid/")      # RFC 6761: কখনো resolve হয় না
        self.assertEqual([(s.layer, s.ok) for s in r.steps], [("dns", False)])

    def test_classify(self) -> None:
        self.assertEqual(nc.classify(ConnectionRefusedError()), "tcp-refused")
        self.assertEqual(nc.classify(TimeoutError()), "tcp-timeout")
        self.assertEqual(nc.classify(OSError(errno.EHOSTUNREACH, "No route to host")), "tcp-unreachable")

    def test_cli_json_and_bad_url(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = nc.main([f"http://127.0.0.1:{self.port}/", "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(buf.getvalue())["ok"])
        self.assertEqual(nc.main(["ftp://example.com/"]), 2)


if __name__ == "__main__":
    unittest.main()
