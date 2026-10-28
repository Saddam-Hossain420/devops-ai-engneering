#!/usr/bin/env python3
"""Graceful worker — signal সঠিকভাবে সামলানোর উদাহরণ (Linux)।

আচরণ:
  SIGTERM / SIGINT → নতুন কাজ নেওয়া বন্ধ, চলমান কাজ শেষ করে exit 0
  SIGHUP           → configuration "reload" (বন্ধ না হয়ে)
  SIGKILL          → ধরা যায় না; process সঙ্গে সঙ্গে মারা যায় (exit 137)

Usage:
  python3 graceful_worker.py --job-seconds 2 &
  kill -HUP %1     # reload
  kill -TERM %1    # graceful stop
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time

stop_requested = False
reload_count = 0


def on_term(signum: int, _frame) -> None:
    # Handler-এ ভারী কাজ নয় — শুধু flag সেট; main loop সিদ্ধান্ত নেয়
    global stop_requested
    stop_requested = True
    print(f"[worker {os.getpid()}] got {signal.Signals(signum).name}, finishing current job", flush=True)


def on_hup(_signum: int, _frame) -> None:
    global reload_count
    reload_count += 1
    print(f"[worker {os.getpid()}] SIGHUP: reloading config (#{reload_count})", flush=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Signal-aware demo worker.")
    p.add_argument("--job-seconds", type=float, default=1.0)
    p.add_argument("--max-jobs", type=int, default=1000)
    args = p.parse_args(argv)

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    if hasattr(signal, "SIGHUP"):  # Windows-এ SIGHUP নেই
        signal.signal(signal.SIGHUP, on_hup)

    print(f"[worker {os.getpid()}] started", flush=True)
    done = 0
    while not stop_requested and done < args.max_jobs:
        # একটি "কাজ": ছোট ছোট ধাপে ঘুম, যাতে signal দ্রুত লক্ষ্য করা যায়
        deadline = time.monotonic() + args.job_seconds
        while time.monotonic() < deadline:
            time.sleep(0.05)
        done += 1
        print(f"[worker {os.getpid()}] job {done} done", flush=True)
    print(f"[worker {os.getpid()}] clean shutdown after {done} job(s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
