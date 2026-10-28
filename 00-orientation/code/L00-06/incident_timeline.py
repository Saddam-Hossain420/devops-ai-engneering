#!/usr/bin/env python3
"""Application log থেকে incident timeline.

Log line format (structured text):
  2026-10-20T14:03:12Z level=ERROR msg="db connection timeout" request_id=abc

Output:
  - প্রতি মিনিটে INFO/WARN/ERROR গণনা ও error rate
  - প্রথম ও শেষ ERROR
  - সবচেয়ে বেশি আসা error message
  - error rate একটি সীমা ছাড়িয়েছে এমন মিনিট (incident window)

Usage:
  python3 incident_timeline.py sample-app.log
  python3 incident_timeline.py sample-app.log --threshold 20
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

LINE_RE = re.compile(r'^(?P<ts>\S+) level=(?P<level>[A-Z]+) msg="(?P<msg>[^"]*)"')
LEVELS = ("INFO", "WARN", "ERROR")


@dataclass(frozen=True)
class Entry:
    ts: datetime
    level: str
    msg: str


def parse_line(line: str) -> Entry | None:
    """ঠিক format না হলে None — ভাঙা লাইনের জন্য পুরো analysis থামে না।"""
    m = LINE_RE.match(line.strip())
    if not m or m["level"] not in LEVELS:
        return None
    try:
        ts = datetime.fromisoformat(m["ts"].replace("Z", "+00:00"))
    except ValueError:
        return None
    return Entry(ts, m["level"], m["msg"])


def load(path: Path) -> tuple[list[Entry], int]:
    entries, skipped = [], 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            e = parse_line(line)
            if e is None:
                skipped += 1
            else:
                entries.append(e)
    return entries, skipped


def per_minute(entries: list[Entry]) -> dict[str, Counter]:
    buckets: dict[str, Counter] = defaultdict(Counter)
    for e in entries:
        buckets[e.ts.strftime("%H:%M")][e.level] += 1
    return dict(sorted(buckets.items()))


def error_rate(c: Counter) -> float:
    total = sum(c.values())
    return 100 * c["ERROR"] / total if total else 0.0


def incident_window(minutes: dict[str, Counter], threshold: float) -> tuple[str, str] | None:
    """Error rate threshold ছাড়ানো প্রথম ও শেষ মিনিট।"""
    bad = [m for m, c in minutes.items() if error_rate(c) >= threshold]
    return (bad[0], bad[-1]) if bad else None


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Build an incident timeline from an application log.")
    p.add_argument("log_file", type=Path)
    p.add_argument("--threshold", type=float, default=20, help="error rate %% for incident window")
    args = p.parse_args(argv)

    try:
        entries, skipped = load(args.log_file)
    except FileNotFoundError:
        print(f"error: file not found: {args.log_file}", file=sys.stderr)
        return 2
    if not entries:
        print("error: no parsable log lines", file=sys.stderr)
        return 2

    minutes = per_minute(entries)
    print(f"{'minute':8}{'INFO':>6}{'WARN':>6}{'ERROR':>7}{'err%':>7}")
    for minute, c in minutes.items():
        rate = error_rate(c)
        flag = "  <-- " if rate >= args.threshold else ""
        print(f"{minute:8}{c['INFO']:>6}{c['WARN']:>6}{c['ERROR']:>7}{rate:>6.0f}%{flag}")

    errors = [e for e in entries if e.level == "ERROR"]
    print(f"\nparsed lines: {len(entries)}   skipped (unparsable): {skipped}")
    if errors:
        print(f"first ERROR : {errors[0].ts:%H:%M:%S}  {errors[0].msg}")
        print(f"last ERROR  : {errors[-1].ts:%H:%M:%S}  {errors[-1].msg}")
        print("top errors  :")
        for msg, count in Counter(e.msg for e in errors).most_common(3):
            print(f"  {count:>3} × {msg}")
    window = incident_window(minutes, args.threshold)
    print(f"incident window (err% >= {args.threshold:g}): "
          f"{f'{window[0]} → {window[1]}' if window else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
