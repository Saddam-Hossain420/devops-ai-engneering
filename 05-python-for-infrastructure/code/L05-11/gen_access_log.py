#!/usr/bin/env python3
"""gen_access_log.py — কৃত্রিম nginx access log (combined + $request_time), একটি incident সহ। Seed স্থির → একই output।

  python3 gen_access_log.py --lines 50000 > access.log
  python3 gen_access_log.py --lines 50000 --gzip > access.log.gz

Incident: শুরু থেকে ২০–২৫ মিনিটে /api/orders-এ 503 ও ধীর response (upstream সমস্যার অনুকরণ)।
IP-গুলো documentation range (RFC 5737)। কিছু লাইন ইচ্ছাকৃত ভাঙা (parser পরীক্ষার জন্য)।
"""
from __future__ import annotations

import argparse
import gzip
import random
import sys
from datetime import UTC, datetime, timedelta

PATHS = [("/", 30), ("/api/tasks", 25), ("/api/orders", 15), ("/static/app.js", 15), ("/login", 10), ("/health", 5)]
IPS = [f"192.0.2.{i}" for i in range(1, 40)] + [f"198.51.100.{i}" for i in range(1, 20)] + ["203.0.113.66"]
START = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


def line_for(rng: random.Random, ts: datetime) -> str:
    path = rng.choices([p for p, _ in PATHS], weights=[w for _, w in PATHS])[0]
    ip = "203.0.113.66" if rng.random() < 0.08 else rng.choice(IPS)        # একটি "ব্যস্ত" client
    minute = (ts - START).total_seconds() / 60
    incident = 20 <= minute < 25 and path == "/api/orders"
    status = rng.choices([200, 201, 304, 404, 500], weights=[80, 5, 8, 6, 1])[0]
    rt = round(rng.lognormvariate(-3.0, 0.6), 3)                            # সাধারণত ~০.০৫ s
    if incident:
        status = 503 if rng.random() < 0.7 else 200
        rt = round(rng.uniform(1.5, 5.0), 3)
    size = 0 if status in (304, 503) else rng.randint(200, 50_000)
    method = "POST" if path == "/login" else "GET"
    return (f'{ip} - - [{ts:%d/%b/%Y:%H:%M:%S} +0000] "{method} {path} HTTP/1.1" {status} {size} '
            f'"-" "Mozilla/5.0 (synthetic)" {rt}')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=50_000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--gzip", action="store_true")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    step = timedelta(hours=1) / args.lines                                  # এক ঘণ্টায় সমানভাবে ছড়ানো
    lines = [line_for(rng, START + i * step) for i in range(args.lines)]
    for i in range(0, args.lines, max(1, args.lines // 5)):
        lines[i] = "this is not an access log line"                         # ভাঙা লাইন
    data = ("\n".join(lines) + "\n").encode()
    sys.stdout.buffer.write(gzip.compress(data, mtime=0) if args.gzip else data)


if __name__ == "__main__":
    main()
