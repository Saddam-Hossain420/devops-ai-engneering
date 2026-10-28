#!/usr/bin/env python3
"""cache_sim.py — nginx proxy_cache: (১) একটি response cache হবে কিনা, কতক্ষণ; (২) cache stampede-এর simulation।

  python3 cache_sim.py decide --status 200 --header 'Cache-Control: max-age=60'
  python3 cache_sim.py decide --status 200 --header 'Set-Cookie: session=abc' --valid 200=10m
  python3 cache_sim.py stampede --clients 200 --upstream-ms 800

সিদ্ধান্তের ক্রম (https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_valid):
  method GET/HEAD নয় → নয় · proxy_no_cache শর্ত সত্য → নয়
  X-Accel-Expires > Cache-Control (no-store/no-cache/private → নয়; s-maxage/max-age) > Expires > proxy_cache_valid
  Set-Cookie থাকলে নয় · Vary: * থাকলে নয়   (proxy_ignore_headers দিয়ে এগুলো উপেক্ষা করা যায় — সতর্কভাবে)
"""
from __future__ import annotations

import argparse
import email.utils
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime


def parse_duration(text: str) -> int:
    total = 0
    for num, unit in re.findall(r"(\d+)\s*([smhdwy]?)", text):
        total += int(num) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}[unit]
    return total


@dataclass
class Decision:
    cache: bool
    ttl: int
    reason: str


@dataclass
class Config:
    valid: dict[str, int] = field(default_factory=dict)        # "200" / "404" / "any" → seconds
    methods: tuple[str, ...] = ("GET", "HEAD")
    ignore: frozenset[str] = frozenset()                       # proxy_ignore_headers (ছোট হাতে)
    no_cache_if: tuple[str, ...] = ()                          # request header নাম; থাকলে cache নয় (proxy_no_cache)


def decide(method: str, req_headers: dict[str, str], status: int, resp_headers: dict[str, str],
           cfg: Config, now: datetime | None = None) -> Decision:
    req = {k.lower(): v for k, v in req_headers.items()}
    resp = {k.lower(): v for k, v in resp_headers.items()}
    if method.upper() not in cfg.methods:
        return Decision(False, 0, f"method {method} not in proxy_cache_methods")
    for h in cfg.no_cache_if:
        if req.get(h.lower()):
            return Decision(False, 0, f"proxy_no_cache: request has {h}")
    if "set-cookie" in resp and "set-cookie" not in cfg.ignore:
        return Decision(False, 0, "response has Set-Cookie (per-user data) — never cached unless ignored")
    if resp.get("vary", "").strip() == "*" and "vary" not in cfg.ignore:
        return Decision(False, 0, "Vary: * — not cacheable")
    if "x-accel-expires" in resp and "x-accel-expires" not in cfg.ignore:
        v = resp["x-accel-expires"].strip()
        if v == "0":
            return Decision(False, 0, "X-Accel-Expires: 0")
        return Decision(True, int(v.lstrip("@")), "X-Accel-Expires (highest priority)")
    if "cache-control" in resp and "cache-control" not in cfg.ignore:
        cc = {d.strip().split("=")[0].lower(): (d.split("=", 1)[1].strip() if "=" in d else "")
              for d in resp["cache-control"].split(",") if d.strip()}
        for directive in ("no-store", "no-cache", "private"):
            if directive in cc:
                return Decision(False, 0, f"Cache-Control: {directive}")
        for directive in ("s-maxage", "max-age"):
            if directive in cc and cc[directive].isdigit():
                ttl = int(cc[directive])
                return Decision(ttl > 0, ttl, f"Cache-Control: {directive}={ttl}")
    if "expires" in resp and "expires" not in cfg.ignore:
        try:
            exp = email.utils.parsedate_to_datetime(resp["expires"])
        except (TypeError, ValueError):
            return Decision(False, 0, "invalid Expires — treated as already expired")
        ref = now or datetime.now(exp.tzinfo)
        ttl = int((exp - ref).total_seconds())
        return Decision(ttl > 0, max(ttl, 0), f"Expires ({ttl}s from now)")
    ttl = cfg.valid.get(str(status), cfg.valid.get("any", 0))
    if ttl > 0:
        return Decision(True, ttl, f"proxy_cache_valid for {status}")
    return Decision(False, 0, f"no caching headers and no proxy_cache_valid for {status}")


def stampede(clients: int, upstream_ms: int, lock: bool, use_stale: bool, spread_ms: int = 50) -> dict[str, float]:
    """একটি জনপ্রিয় entry মেয়াদোত্তীর্ণ — `clients` জন `spread_ms`-এর মধ্যে আসে। upstream কতবার? client কতক্ষণ?"""
    arrivals = [i * spread_ms / max(clients - 1, 1) for i in range(clients)]
    upstream_calls, waits = 0, []
    refresh_done_at: float | None = None
    for t in arrivals:
        if refresh_done_at is not None and t >= refresh_done_at:
            waits.append(0.0)                                   # নতুন entry তৈরি — HIT
        elif refresh_done_at is None:
            upstream_calls += 1                                 # প্রথমজন upstream-এ যায়
            refresh_done_at = t + upstream_ms
            waits.append(upstream_ms)
        elif use_stale:
            waits.append(0.0)                                   # STALE: পুরোনো copy সাথে সাথে (updating)
        elif lock:
            waits.append(refresh_done_at - t)                   # lock: প্রথমজনের শেষের অপেক্ষা
        else:
            upstream_calls += 1                                 # lock নেই: প্রত্যেকে নিজে upstream-এ
            waits.append(upstream_ms)
    waits.sort()
    return {"upstream_calls": upstream_calls, "max_wait_ms": round(waits[-1], 1),
            "median_wait_ms": round(waits[len(waits) // 2], 1)}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Simulate nginx proxy_cache decisions and cache stampedes.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decide")
    d.add_argument("--method", default="GET")
    d.add_argument("--status", type=int, default=200)
    d.add_argument("--header", action="append", default=[], help="response header 'Name: value'")
    d.add_argument("--req-header", action="append", default=[], help="request header 'Name: value'")
    d.add_argument("--valid", action="append", default=[], help="proxy_cache_valid, e.g. 200=10m any=1m")
    d.add_argument("--ignore", action="append", default=[], help="proxy_ignore_headers, e.g. Set-Cookie")
    d.add_argument("--no-cache-if", action="append", default=[], help="request header that bypasses, e.g. Authorization")
    s = sub.add_parser("stampede")
    s.add_argument("--clients", type=int, default=200)
    s.add_argument("--upstream-ms", type=int, default=800)
    a = ap.parse_args(argv)
    if a.cmd == "decide":
        def hdrs(items: list[str]) -> dict[str, str]:
            return {k.strip(): v.strip() for k, _, v in (h.partition(":") for h in items)}
        cfg = Config({k: parse_duration(v) for k, _, v in (x.partition("=") for x in a.valid)},
                     ignore=frozenset(h.lower() for h in a.ignore), no_cache_if=tuple(a.no_cache_if))
        r = decide(a.method, hdrs(a.req_header), a.status, hdrs(a.header), cfg)
        print(f"{'CACHE' if r.cache else 'NO CACHE':<9} ttl={r.ttl}s  ← {r.reason}")
        return 0
    print(f"{a.clients} clients within 50 ms on an expired entry, upstream takes {a.upstream_ms} ms")
    for label, lock, stale in (("no lock", False, False), ("proxy_cache_lock on", True, False),
                               ("use_stale updating", False, True)):
        r = stampede(a.clients, a.upstream_ms, lock, stale)
        print(f"  {label:<22} upstream calls {r['upstream_calls']:>4}   median wait {r['median_wait_ms']:>6} ms"
              f"   max wait {r['max_wait_ms']:>6} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
