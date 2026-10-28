"""Tests for lb_algorithms.py and mini_proxy.py — চালানো: python3 -m unittest -v

Proxy test loopback-এ আসল HTTP backend ও proxy চালায়।
"""
from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import lb_algorithms as lb  # noqa: E402
import mini_proxy as mp  # noqa: E402


class AlgorithmTest(unittest.TestCase):
    def test_round_robin(self) -> None:
        rr = lb.RoundRobin(["a", "b", "c"])
        self.assertEqual([rr.pick() for _ in range(5)], ["a", "b", "c", "a", "b"])

    def test_smooth_weighted_sequence(self) -> None:
        sw = lb.SmoothWeighted({"a": 5, "b": 1, "c": 1})
        self.assertEqual("".join(sw.pick() for _ in range(7)), "aabacaa")   # nginx-এর পরিচিত ক্রম

    def test_least_connections(self) -> None:
        lc = lb.LeastConnections(["a", "b"])
        self.assertEqual(lc.pick(), "a")         # a ব্যস্ত হলো
        self.assertEqual(lc.pick(), "b")
        lc.done("b")
        self.assertEqual(lc.pick(), "b")         # a এখনো ব্যস্ত

    def test_consistent_hash_stable_and_balanced(self) -> None:
        servers = ["s1", "s2", "s3"]
        ch = lb.ConsistentHash(servers)
        self.assertEqual(ch.pick("user-42"), lb.ConsistentHash(servers).pick("user-42"))
        counts = Counter(ch.pick(f"k{i}") for i in range(9000))
        self.assertTrue(all(2000 < c < 4000 for c in counts.values()), counts)

    def test_remap(self) -> None:
        before = [f"c{i}" for i in range(4)]
        after = before + ["c4"]
        self.assertGreater(lb.remap_fraction(lb.ModuloHash, before, after), 0.6)
        self.assertLess(lb.remap_fraction(lb.ConsistentHash, before, after), 0.3)


class ProxyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.servers = []

    def tearDown(self) -> None:
        for s in self.servers:
            mp.stop(s)

    def backend(self, name: str, delay: float = 0.0) -> str:
        srv, port = mp.start_backend(name, delay)
        self.servers.append(srv)
        return f"127.0.0.1:{port}"

    def proxy(self, backends: list[str], **kw: float) -> int:
        srv, port = mp.start_proxy(backends, **kw)
        self.servers.append(srv)
        return port

    def test_balances_and_skips_dead(self) -> None:
        backends = [self.backend("a"), f"127.0.0.1:{mp.dead_port()}", self.backend("b")]
        port = self.proxy(backends)
        seen = []
        for _ in range(6):
            status, hdrs, body = mp.get(port)
            self.assertEqual(status, 200)
            info = json.loads(body)
            seen.append(info["backend"])
            self.assertEqual(info["x_forwarded_for"], "127.0.0.1")
            self.assertEqual(info["x_request_id"], hdrs["X-Request-ID"])   # একই ID দুই দিকে
        self.assertEqual(Counter(seen), Counter({"a": 3, "b": 3}))

    def test_all_dead_502(self) -> None:
        port = self.proxy([f"127.0.0.1:{mp.dead_port()}"])
        status, _, body = mp.get(port)
        self.assertEqual(status, 502)
        self.assertIn(b"no backend reachable", body)

    def test_slow_backend_504(self) -> None:
        port = self.proxy([self.backend("slow", delay=1.0)], timeout=0.3)
        status, hdrs, _ = mp.get(port)
        self.assertEqual(status, 504)
        self.assertIn("X-Request-ID", hdrs)


if __name__ == "__main__":
    unittest.main()
