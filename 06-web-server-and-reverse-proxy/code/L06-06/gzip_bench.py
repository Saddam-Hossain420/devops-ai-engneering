#!/usr/bin/env python3
"""gzip_bench.py — gzip কতটা ছোট করে, কত CPU খরচে: level ১/৫/৯, আসল ধরনের data-য়।

  python3 gzip_bench.py

Data: TaskFlow-ধাঁচের JSON (১০০ task), এই repository-র একটি lesson markdown (text), এলোমেলো bytes
(JPEG/ZIP-এর মতো আগে থেকে compressed), এবং একটি ছোট JSON (৮০ byte) — gzip_min_length কেন।
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def samples() -> dict[str, bytes]:
    tasks = {"items": [{"id": i, "title": f"task number {i} for the release checklist", "done": i % 3 == 0,
                        "created_at": "2026-10-27T03:18:45+00:00", "updated_at": "2026-10-27T03:18:46+00:00"}
                       for i in range(1, 101)], "total": 100, "limit": 100, "offset": 0}
    lesson = (HERE.parent.parent / "L06-02-nginx-architecture.md").read_bytes()
    return {
        "taskflow JSON (100 tasks)": json.dumps(tasks).encode(),
        "lesson markdown (UTF-8 text)": lesson,
        "random bytes (like JPEG/ZIP)": os.urandom(200_000),
        "tiny JSON": b'{"status": "ok", "version": "0.1.0"}',
    }


def bench(data: bytes, level: int, min_seconds: float = 0.3) -> tuple[int, float]:
    """নির্দিষ্ট সংখ্যক বার নয়, অন্তত `min_seconds` পর্যন্ত — ছোট input-এ timer-এর শব্দ এড়াতে।"""
    runs, start = 0, time.perf_counter()
    while True:
        out = gzip.compress(data, compresslevel=level, mtime=0)
        runs += 1
        elapsed = time.perf_counter() - start
        if elapsed >= min_seconds:
            return len(out), elapsed / runs


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"{'payload':<30} {'bytes':>8}   level 1          level 5          level 9")
    for name, data in samples().items():
        cells = []
        for level in (1, 5, 9):
            size, t = bench(data, level)
            mb_s = len(data) / t / 1e6 if t else float("inf")
            cells.append(f"{size / len(data):5.0%} {mb_s:6.0f} MB/s")
        print(f"{name:<30} {len(data):>8}   " + "   ".join(cells))


if __name__ == "__main__":
    main()
