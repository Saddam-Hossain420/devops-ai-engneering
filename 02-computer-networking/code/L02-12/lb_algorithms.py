#!/usr/bin/env python3
"""Load-balancing algorithm — round robin, smooth weighted round robin, least connections, consistent hashing।

  python3 lb_algorithms.py compare            # ১০০০০ request-এ বণ্টন
  python3 lb_algorithms.py remap --from 4     # server যোগ হলে কত key অন্য server-এ যায়: modulo বনাম ring

শুধু simulation, network ব্যবহার করে না।
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import sys
from collections import Counter


class RoundRobin:
    def __init__(self, servers: list[str]) -> None:
        self.servers, self.i = servers, -1

    def pick(self, key: str = "") -> str:
        self.i = (self.i + 1) % len(self.servers)
        return self.servers[self.i]


class SmoothWeighted:
    """Nginx-এর smooth weighted round robin: ভারী server-কেও একটানা নয়, ছড়িয়ে বাছাই করে।"""

    def __init__(self, weights: dict[str, int]) -> None:
        self.weights = weights
        self.current = {s: 0 for s in weights}
        self.total = sum(weights.values())

    def pick(self, key: str = "") -> str:
        for s, w in self.weights.items():
            self.current[s] += w
        best = max(self.current, key=lambda s: self.current[s])
        self.current[best] -= self.total
        return best


class LeastConnections:
    """সবচেয়ে কম active connection; সমান হলে list-এর আগেরটি। দীর্ঘ/অসম request-এ round robin-এর চেয়ে ভালো।"""

    def __init__(self, servers: list[str]) -> None:
        self.active = {s: 0 for s in servers}

    def pick(self, key: str = "") -> str:
        s = min(self.active, key=lambda x: self.active[x])
        self.active[s] += 1
        return s

    def done(self, server: str) -> None:
        self.active[server] -= 1


def h(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big")


class ModuloHash:
    """hash(key) % N — সরল, কিন্তু N বদলালে প্রায় সব key অন্য server-এ যায়।"""

    def __init__(self, servers: list[str]) -> None:
        self.servers = servers

    def pick(self, key: str) -> str:
        return self.servers[h(key) % len(self.servers)]


class ConsistentHash:
    """Hash ring + virtual node: server যোগ/বাদে শুধু ~1/N key সরে। Cache, sticky session, sharding-এ।"""

    def __init__(self, servers: list[str], vnodes: int = 100) -> None:
        self.ring: list[tuple[int, str]] = sorted((h(f"{s}#{i}"), s) for s in servers for i in range(vnodes))
        self.points = [p for p, _ in self.ring]

    def pick(self, key: str) -> str:
        i = bisect.bisect(self.points, h(key)) % len(self.ring)  # ঘড়ির কাঁটার দিকে পরের point
        return self.ring[i][1]


def remap_fraction(make, before: list[str], after: list[str], keys: int = 10000) -> float:
    a, b = make(before), make(after)
    moved = sum(a.pick(f"user-{k}") != b.pick(f"user-{k}") for k in range(keys))
    return moved / keys


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Compare load-balancing algorithms.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("compare")
    r = sub.add_parser("remap")
    r.add_argument("--from", dest="n", type=int, default=4)
    args = ap.parse_args(argv)

    if args.cmd == "compare":
        servers = ["app-1", "app-2", "app-3"]
        rr = RoundRobin(servers)
        print("round robin        ", dict(Counter(rr.pick() for _ in range(9999))))
        sw = SmoothWeighted({"big": 5, "small-1": 1, "small-2": 1})
        print("smooth weighted 5:1:1 first 7 picks:", " ".join(sw.pick() for _ in range(7)))
        ch = ConsistentHash(servers)
        print("consistent hash    ", dict(Counter(ch.pick(f"user-{k}") for k in range(9999))))
        lc = LeastConnections(servers)
        # app-1-এ একটি দীর্ঘ request আটকে আছে; বাকি request ছোট ও সাথে সাথে শেষ
        lc.pick()
        picks = []
        for _ in range(6):
            s = lc.pick()
            picks.append(s)
            lc.done(s)
        print("least connections (app-1 busy with a long request):", " ".join(picks))
    else:
        if args.n < 1:
            print("error: --from must be >= 1", file=sys.stderr)
            return 2
        before = [f"cache-{i}" for i in range(1, args.n + 1)]
        after = before + [f"cache-{args.n + 1}"]
        ideal = 1 / (args.n + 1)
        print(f"{args.n} → {args.n + 1} servers, 10000 keys (ideal: {ideal:.1%} move)")
        print(f"  modulo hash:     {remap_fraction(ModuloHash, before, after):.1%} of keys moved")
        print(f"  consistent hash: {remap_fraction(ConsistentHash, before, after):.1%} of keys moved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
