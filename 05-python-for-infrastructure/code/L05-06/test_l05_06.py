"""Tests for http_client.py — চালানো: python3 -m unittest -v

প্রতিটি test class নিজের local flaky_server (127.0.0.1, OS-নির্বাচিত port) চালায় — internet লাগে না।
Backoff-এর sleep আসলে ঘুমায় না; delay-গুলো list-এ জমা হয় (test দ্রুত ও নির্ভরযোগ্য)।
"""
from __future__ import annotations

import socket
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flaky_server  # noqa: E402
import http_client as hc  # noqa: E402


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.httpd = flaky_server.serve(0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self) -> None:
        hc.request(self.base + "/reset")
        self.sleeps: list[float] = []

    def call(self, path: str, **kw: object) -> hc.Response:
        return hc.request(self.base + path, sleep=self.sleeps.append, **kw)  # type: ignore[arg-type]

    def test_retry_until_success(self) -> None:
        r = self.call("/flaky", retries=3)
        self.assertEqual((r.status, r.attempts), (200, 3))
        self.assertEqual(len(self.sleeps), 2)
        self.assertEqual(r.json()["call"], 3)

    def test_gives_up_and_returns_last_response(self) -> None:
        r = self.call("/flaky", retries=1)
        self.assertEqual((r.status, r.attempts, r.ok), (503, 2, False))

    def test_retry_after_is_honoured(self) -> None:
        r = self.call("/ratelimit")
        self.assertEqual(r.status, 200)
        self.assertEqual(self.sleeps, [1.0])                     # jitter নয়, server-এর কথা

    def test_retry_after_too_long_is_not_waited(self) -> None:
        r = self.call("/ratelimit", max_retry_after=0.5)
        self.assertEqual((r.status, r.attempts, self.sleeps), (429, 1, []))

    def test_4xx_not_retried(self) -> None:
        r = self.call("/notfound", retries=5)
        self.assertEqual((r.status, r.attempts, self.sleeps), (404, 1, []))

    def test_post_not_retried_without_key(self) -> None:
        r = self.call("/flaky", method="POST", body=b"{}", retries=5)
        self.assertEqual(r.attempts, 1)                          # /flaky POST → 404, একবারই

    def test_idempotency_key_dedupes_on_server(self) -> None:
        a = self.call("/orders", method="POST", body=b"{}", idempotency_key="k1")
        b = self.call("/orders", method="POST", body=b"{}", idempotency_key="k1")
        c = self.call("/orders", method="POST", body=b"{}")
        self.assertEqual(a.json(), b.json())
        self.assertNotEqual(a.json(), c.json())

    def test_timeout_raises_after_retries(self) -> None:
        start = time.monotonic()
        with self.assertRaises(hc.RequestFailedError) as cm:
            self.call("/slow?s=2", timeout=0.3, retries=1)
        self.assertEqual(cm.exception.attempts, 2)
        self.assertLess(time.monotonic() - start, 1.8)            # ২ × ০.৩ s timeout, ২ s নয়


class OfflineTest(unittest.TestCase):
    def test_connection_failure(self) -> None:
        with socket.socket() as s:                                 # খালি port খুঁজে বন্ধ করা
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        sleeps: list[float] = []
        with self.assertRaises(hc.RequestFailedError) as cm:
            hc.request(f"http://127.0.0.1:{port}/", timeout=3, retries=2, sleep=sleeps.append)
        self.assertEqual((cm.exception.attempts, len(sleeps)), (3, 2))

    def test_backoff_is_bounded_full_jitter(self) -> None:
        self.assertEqual([hc.backoff_delay(a, 0.5, 4, rng=lambda: 1.0) for a in range(5)],
                         [0.5, 1.0, 2.0, 4.0, 4.0])
        self.assertEqual(hc.backoff_delay(3, 0.5, 4, rng=lambda: 0.0), 0.0)

    def test_retry_after_formats(self) -> None:
        self.assertEqual(hc.retry_after_seconds("7"), 7.0)
        self.assertEqual(hc.retry_after_seconds("Wed, 21 Oct 2015 07:28:10 GMT", now=1445412480.0), 10.0)
        self.assertIsNone(hc.retry_after_seconds("soon"))


if __name__ == "__main__":
    unittest.main()
