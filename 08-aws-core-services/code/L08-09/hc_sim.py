#!/usr/bin/env python3
"""hc_sim.py — ALB-এর health-check নিয়ম (interval, timeout, healthy/unhealthy threshold, matcher) local URL-এ চালানো;
প্রতিটি state পরিবর্তন সময়সহ ছাপে। আসল load balancer নয় — নিয়মটি নিজের চোখে দেখা ও মাপার জন্য।

  # দুই terminal-এ TaskFlow (L05-13): TASKFLOW_PORT=8001 … , TASKFLOW_PORT=8002 …
  python3 hc_sim.py http://127.0.0.1:8001/health http://127.0.0.1:8002/health --interval 2 --unhealthy 2 --healthy 3
  # তারপর একটি বন্ধ করুন (Ctrl-C) — কত সেকেন্ডে "unhealthy" হয়? আবার চালু করুন — কত সেকেন্ডে "healthy"?
"""
from __future__ import annotations

import argparse
import http.client
import sys
import time
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass
class Target:
    url: str
    state: str = "initial"
    ok_streak: int = 0
    fail_streak: int = 0
    last: str = ""


def probe(url: str, timeout: float, matcher: set[int]) -> tuple[bool, str]:
    u = urlsplit(url)
    conn = http.client.HTTPConnection(u.hostname or "127.0.0.1", u.port or 80, timeout=timeout)
    try:
        conn.request("GET", u.path or "/", headers={"User-Agent": "ELB-HealthChecker-sim"})
        status = conn.getresponse().status
        return status in matcher, f"HTTP {status}"
    except TimeoutError:
        return False, "timeout"
    except OSError as exc:
        return False, type(exc).__name__
    finally:
        conn.close()


def step(t: Target, ok: bool, detail: str, healthy_n: int, unhealthy_n: int) -> str | None:
    """একটি check-এর ফল প্রয়োগ; state বদলালে নতুন state ফেরত।"""
    t.last = detail
    if ok:
        t.ok_streak, t.fail_streak = t.ok_streak + 1, 0
        if t.state != "healthy" and t.ok_streak >= healthy_n:
            t.state = "healthy"
            return t.state
    else:
        t.fail_streak, t.ok_streak = t.fail_streak + 1, 0
        if t.state != "unhealthy" and t.fail_streak >= unhealthy_n:
            t.state = "unhealthy"
            return t.state
    return None


def run(targets: list[Target], interval: float, timeout: float, healthy_n: int, unhealthy_n: int,
        matcher: set[int], rounds: int | None, out=sys.stdout) -> list[tuple[float, str, str, str]]:
    start = time.monotonic()
    events: list[tuple[float, str, str, str]] = []
    n = 0
    while rounds is None or n < rounds:
        tick = time.monotonic()
        for t in targets:
            ok, detail = probe(t.url, timeout, matcher)
            changed = step(t, ok, detail, healthy_n, unhealthy_n)
            if changed:
                events.append((tick - start, t.url, changed, detail))
                print(f"{tick - start:7.1f}s  {t.url:<34} → {changed:<9} ({detail})", file=out, flush=True)
        n += 1
        time.sleep(max(0.0, interval - (time.monotonic() - tick)))
    return events


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Simulate ALB health checks against local URLs.")
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--interval", type=float, default=30)
    ap.add_argument("--timeout", type=float, default=5)
    ap.add_argument("--healthy", type=int, default=5)
    ap.add_argument("--unhealthy", type=int, default=2)
    ap.add_argument("--matcher", default="200")
    ap.add_argument("--rounds", type=int)
    a = ap.parse_args(argv)
    if a.timeout >= a.interval:
        print("error: timeout must be smaller than interval (as on ALB)", file=sys.stderr)
        return 2
    matcher = {int(c) for c in a.matcher.split(",")}
    print(f"interval {a.interval}s, timeout {a.timeout}s, healthy after {a.healthy}, unhealthy after {a.unhealthy} "
          f"→ detect ≈{a.interval * a.unhealthy:g}s, readmit ≈{a.interval * a.healthy:g}s")
    try:
        run([Target(u) for u in a.urls], a.interval, a.timeout, a.healthy, a.unhealthy, matcher, a.rounds)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
