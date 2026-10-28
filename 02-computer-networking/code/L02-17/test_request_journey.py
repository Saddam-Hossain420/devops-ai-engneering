"""Tests for request_journey.py — চালানো: python3 -m unittest -v

প্রতিটি test loopback-এ পুরো stack (proxy, app, temporary SQLite) চালায়।
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import request_journey as rj  # noqa: E402


def hops(log: rj.Log, rid: str) -> dict[str, dict]:
    return {l["hop"]: l for l in log.for_request(rid)}


class JourneyTest(unittest.TestCase):
    def test_normal_request_one_id_everywhere(self) -> None:
        with rj.Stack() as st:
            status, rid, timing = st.request("/items/1")
            self.assertEqual(status, 200)
            h = hops(st.log, rid)
            self.assertEqual(set(h), {"client", "proxy", "app", "db"})     # একই ID চারটি hop-এ
            self.assertTrue(h["proxy"]["upstream_ms"] >= h["app"]["db_ms"])
            self.assertTrue(timing["total_ms"] >= timing["ttfb_ms"])

    def test_not_found(self) -> None:
        with rj.Stack() as st:
            status, rid, _ = st.request("/items/99")
            self.assertEqual(status, 404)
            self.assertEqual(hops(st.log, rid)["db"]["ok"], True)          # DB ঠিক, শুধু row নেই

    def test_db_slow_gives_504_and_wasted_work(self) -> None:
        with rj.Stack("db-slow") as st:
            status, rid, timing = st.request("/items/1")
            self.assertEqual(status, 504)
            self.assertLess(timing["total_ms"], 1400)                     # proxy timeout ১ সেকেন্ড
            time.sleep(1.0)                                               # app-এর কাজ শেষ হোক
            app = hops(st.log, rid)["app"]
            self.assertEqual(app["status"], 200)                          # app সফল হয়েছিল...
            self.assertGreaterEqual(app["db_ms"], 1500)

    def test_app_down_gives_502(self) -> None:
        with rj.Stack("app-down") as st:
            status, rid, _ = st.request("/items/1")
            self.assertEqual(status, 502)
            self.assertEqual(set(hops(st.log, rid)), {"client", "proxy"})

    def test_db_error_gives_500_without_leaking(self) -> None:
        with rj.Stack("db-error") as st:
            status, rid, _ = st.request("/items/1")
            self.assertEqual(status, 500)
            h = hops(st.log, rid)
            self.assertIn("no such table", h["db"]["error"])              # log-এ বিস্তারিত
            self.assertEqual(h["proxy"]["status"], 500)

    def test_cli(self) -> None:
        self.assertEqual(rj.main(["--fault", "app-down"]), 0)


if __name__ == "__main__":
    unittest.main()
