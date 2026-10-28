#!/usr/bin/env python3
"""ইচ্ছাকৃত ধীর একটি "report" — profiling অনুশীলনের জন্য।

একটি function-এ O(n²) duplicate খোঁজা, অন্যটি দ্রুত। Profiler দেখাবে সময় কোথায় যায়।

Usage:
  python3 slow_app.py --n 3000
  python3 -m cProfile -s cumulative slow_app.py --n 3000 | head -20
"""
from __future__ import annotations

import argparse
import random


def make_ids(n: int, seed: int = 42) -> list[int]:
    rng = random.Random(seed)
    return [rng.randrange(n * 10) for _ in range(n)]


def find_duplicates_slow(ids: list[int]) -> set[int]:
    """O(n²): প্রতিটি উপাদানের জন্য বাকি তালিকা খোঁজে।"""
    dups = set()
    for i, x in enumerate(ids):
        if x in ids[i + 1:]:   # slice + linear search — প্রতিবার
            dups.add(x)
    return dups


def find_duplicates_fast(ids: list[int]) -> set[int]:
    """O(n): set দিয়ে একবারে।"""
    seen: set[int] = set()
    dups: set[int] = set()
    for x in ids:
        (dups if x in seen else seen).add(x)
    return dups


def format_report(dups: set[int]) -> str:
    return ", ".join(str(d) for d in sorted(dups))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=3000)
    p.add_argument("--fast", action="store_true")
    args = p.parse_args(argv)
    ids = make_ids(args.n)
    dups = (find_duplicates_fast if args.fast else find_duplicates_slow)(ids)
    report = format_report(dups)
    print(f"{len(dups)} duplicate ids; report length {len(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
