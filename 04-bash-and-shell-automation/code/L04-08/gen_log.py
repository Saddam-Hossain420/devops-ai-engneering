#!/usr/bin/env python3
"""Synthetic access log তৈরি (nginx combined format-এর মতো) — Bash বনাম Python তুলনার জন্য।

  python3 gen_log.py 200000 > access.log
  python3 gen_log.py 50 --tricky > tricky.log     # অদ্ভুত কিন্তু বৈধ লাইন (quote, space, unicode)

নির্দিষ্ট seed — প্রতিবার একই file। কোনো আসল traffic নয়।
"""
from __future__ import annotations

import argparse
import random
import sys

PATHS = ["/", "/api/tasks", "/api/tasks/42", "/login", "/static/app.js", "/api/report", "/health"]
STATUS = [200] * 85 + [301] * 3 + [404] * 6 + [500] * 4 + [503] * 2


def line(rng: random.Random, i: int) -> str:
    ip = f"10.0.{rng.randint(0, 9)}.{rng.randint(1, 254)}"
    path = rng.choice(PATHS)
    status = rng.choice(STATUS)
    size = rng.randint(100, 50_000)
    t = f"27/Oct/2026:10:{(i // 60) % 60:02d}:{i % 60:02d} +0000"
    return f'{ip} - - [{t}] "GET {path} HTTP/1.1" {status} {size} "-" "curl/8.5.0"'


TRICKY = [
    # path-এ quote — nginx নিজেই \" লেখে; সরল printf-JSON-এ কাকতালীয়ভাবে বৈধ থাকে (পরীক্ষায় দেখা)
    '10.0.0.1 - - [27/Oct/2026:10:00:01 +0000] "GET /search?q=\\"rm\\" HTTP/1.1" 500 10 "-" "curl/8.5.0"',
    # path-এ unicode
    '10.0.0.2 - - [27/Oct/2026:10:00:02 +0000] "GET /খোঁজ HTTP/1.1" 500 10 "-" "Mozilla/5.0 (X11; Linux)"',
    # user agent-এ space ও quote — সরল split ভুল column দেয়
    '10.0.0.3 - - [27/Oct/2026:10:00:03 +0000] "GET /api/tasks HTTP/1.1" 503 10 "-" "Bot \\"v2\\" (x)"',
    # অসম্পূর্ণ লাইন (log rotation-এর মাঝে কাটা)
    '10.0.0.4 - - [27/Oct/2026:10:00:04 +0000] "GET /api/tas',
    # path-এ encode না করা space (ভুলভাবে তৈরি client বা আক্রমণ) — field-ভিত্তিক parsing-এ column সরে যায়
    '10.0.0.6 - - [27/Oct/2026:10:00:06 +0000] "GET /my file.txt HTTP/1.1" 502 10 "-" "curl/8.5.0"',
    # backslash
    '10.0.0.5 - - [27/Oct/2026:10:00:05 +0000] "GET /a\\\\b HTTP/1.1" 500 10 "-" "curl/8.5.0"',
]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a synthetic access log.")
    ap.add_argument("n", type=int)
    ap.add_argument("--tricky", action="store_true", help="append edge-case lines")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):                   # test-এ stdout একটি StringIO হতে পারে
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")   # unicode path ও LF — সব OS-এ একই file
    rng = random.Random(42)
    out = sys.stdout
    for i in range(args.n):
        out.write(line(rng, i) + "\n")
    if args.tricky:
        out.write("\n".join(TRICKY) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
