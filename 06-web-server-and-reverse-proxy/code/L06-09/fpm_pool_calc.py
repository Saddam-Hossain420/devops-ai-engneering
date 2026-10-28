#!/usr/bin/env python3
"""fpm_pool_calc.py — PHP-FPM pool-এর pm.max_children ও সংশ্লিষ্ট মান memory থেকে হিসাব।

  python3 fpm_pool_calc.py --ram-mb 2048 --reserved-mb 700 --avg-proc-mb 60
  ps -o rss= -C php-fpm8.3 | python3 fpm_pool_calc.py --ram-mb 2048 --reserved-mb 700 --rss-stdin

মূল নিয়ম: max_children × গড় process memory ≤ PHP-এর জন্য রাখা memory। বেশি দিলে traffic spike-এ swap/OOM —
তখন সব request ধীর বা OOM killer database মেরে ফেলে (L01-09)। কম দিলে request queue-তে অপেক্ষা ("server reached
pm.max_children" warning) — এটা অন্তত নিয়ন্ত্রিত ব্যর্থতা।
"""
from __future__ import annotations

import argparse
import statistics
import sys


def calc(ram_mb: int, reserved_mb: int, avg_proc_mb: float, headroom: float = 0.9) -> dict[str, int | float | str]:
    if avg_proc_mb <= 0:
        raise ValueError("average process memory must be > 0")
    budget = max(0, ram_mb - reserved_mb) * headroom
    children = int(budget // avg_proc_mb)
    if children < 2:
        raise ValueError(f"only {budget:.0f} MB for PHP — not enough for 2 workers of {avg_proc_mb:.0f} MB")
    start = max(1, children // 4)
    return {"php_budget_mb": round(budget), "pm": "dynamic", "pm.max_children": children,
            "pm.start_servers": start, "pm.min_spare_servers": max(1, children // 8) if children >= 8 else 1,
            "pm.max_spare_servers": max(start, children // 2), "pm.max_requests": 500,
            "note": "pm = ondemand for small/rarely used sites (memory freed when idle); static for steady high load"}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Size a PHP-FPM pool from memory.")
    ap.add_argument("--ram-mb", type=int, required=True)
    ap.add_argument("--reserved-mb", type=int, required=True, help="OS + nginx + database + others")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--avg-proc-mb", type=float)
    g.add_argument("--rss-stdin", action="store_true", help="read RSS values in KB (ps -o rss=) from stdin")
    a = ap.parse_args(argv)
    if a.rss_stdin:
        values = [int(x) / 1024 for x in sys.stdin.read().split() if x.isdigit()]
        if not values:
            print("error: no RSS values on stdin", file=sys.stderr)
            return 2
        avg = statistics.mean(values) * 1.2                     # শীর্ষ request-এ বড় হয় — ২০% সতর্কতা
        print(f"measured {len(values)} processes, mean RSS {statistics.mean(values):.1f} MB → using {avg:.1f} MB")
    else:
        avg = a.avg_proc_mb
    try:
        result = calc(a.ram_mb, a.reserved_mb, avg)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for k, v in result.items():
        print(f"{k:<22} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
