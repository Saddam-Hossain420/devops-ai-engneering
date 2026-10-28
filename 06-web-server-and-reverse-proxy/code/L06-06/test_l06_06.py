"""Tests for cache_sim.py ও gzip_bench.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import gzip
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cache_sim as cs  # noqa: E402
import gzip_bench as gb  # noqa: E402

CFG = cs.Config(valid={"200": 600, "404": 60})


def decide(status: int = 200, method: str = "GET", req: dict[str, str] | None = None, **resp: str) -> cs.Decision:
    headers = {k.replace("_", "-"): v for k, v in resp.items()}
    return cs.decide(method, req or {}, status, headers, CFG, now=datetime(2026, 10, 27, tzinfo=UTC))


class DecideTest(unittest.TestCase):
    def test_precedence(self) -> None:
        self.assertEqual(decide(X_Accel_Expires="30", Cache_Control="max-age=600").ttl, 30)
        self.assertEqual(decide(Cache_Control="max-age=60", Expires="Wed, 28 Oct 2026 00:00:00 GMT").ttl, 60)
        self.assertEqual(decide(Cache_Control="s-maxage=120, max-age=60").ttl, 120)        # shared cache-এর জন্য s-maxage
        self.assertEqual(decide(Expires="Tue, 27 Oct 2026 00:05:00 GMT").ttl, 300)
        self.assertEqual(decide().ttl, 600)                                                 # proxy_cache_valid
        self.assertEqual(decide(404).ttl, 60)

    def test_never_cached(self) -> None:
        cases = [decide(Set_Cookie="session=abc"), decide(Cache_Control="private, max-age=600"),
                 decide(Cache_Control="no-store"), decide(Vary="*"), decide(method="POST"),
                 decide(X_Accel_Expires="0"), decide(500), decide(Expires="garbage")]
        self.assertEqual([d.cache for d in cases], [False] * len(cases))

    def test_taskflow_says_no_store(self) -> None:
        # L05-13-এর TaskFlow প্রতিটি response-এ Cache-Control: no-store পাঠায় — proxy_cache_valid থাকলেও cache নয়
        self.assertFalse(decide(Cache_Control="no-store").cache)

    def test_ignore_headers_and_bypass(self) -> None:
        cfg = cs.Config(valid={"200": 600}, ignore=frozenset({"set-cookie"}), no_cache_if=("Authorization",))
        self.assertTrue(cs.decide("GET", {}, 200, {"Set-Cookie": "a=b"}, cfg).cache)           # বিপজ্জনক কিন্তু সম্ভব
        self.assertFalse(cs.decide("GET", {"authorization": "Bearer x"}, 200, {}, cfg).cache)

    def test_durations(self) -> None:
        self.assertEqual([cs.parse_duration(x) for x in ("10m", "1h30m", "45", "1d")], [600, 5400, 45, 86400])


class StampedeTest(unittest.TestCase):
    def test_lock_and_stale(self) -> None:
        self.assertEqual(cs.stampede(200, 800, lock=False, use_stale=False)["upstream_calls"], 200)
        locked = cs.stampede(200, 800, lock=True, use_stale=False)
        stale = cs.stampede(200, 800, lock=False, use_stale=True)
        self.assertEqual((locked["upstream_calls"], stale["upstream_calls"]), (1, 1))
        self.assertGreater(locked["median_wait_ms"], 500)          # lock: সবাই অপেক্ষা করে
        self.assertEqual(stale["median_wait_ms"], 0.0)             # stale: শুধু প্রথমজন অপেক্ষা করে


class GzipTest(unittest.TestCase):
    def test_what_compresses(self) -> None:
        s = gb.samples()
        size = {k: len(gzip.compress(v, 6, mtime=0)) / len(v) for k, v in s.items()}
        self.assertLess(size["taskflow JSON (100 tasks)"], 0.10)
        self.assertGreater(size["random bytes (like JPEG/ZIP)"], 1.0)    # আগে-compressed data বড় হয়
        self.assertGreater(size["tiny JSON"], 1.0)                       # gzip_min_length কেন

    def test_bench_returns_positive_time(self) -> None:
        size, t = gb.bench(b"x" * 1000, 1, min_seconds=0.01)
        self.assertGreater(t, 0)
        self.assertLess(size, 100)


if __name__ == "__main__":
    unittest.main()
