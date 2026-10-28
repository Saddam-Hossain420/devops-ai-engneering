#!/usr/bin/env python3
"""Nginx access log report — shell pipeline-এর (grep | awk | sort | uniq -c) Python সমতুল্য।

Log format: Nginx "combined" + শেষে request time (সেকেন্ডে), যেমন:
  203.0.113.10 - - [26/Oct/2026:09:00:00 +0000] "GET /tasks HTTP/1.1" 200 8585 "-" "curl/8.5.0" 0.052

Usage:
  python3 access_report.py access.log
  python3 access_report.py access.log --top 3 --slow 1.0
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

LINE_RE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) [^"]*" '
    r'(?P<status>\d{3}) (?P<size>\d+|-) "[^"]*" "(?P<agent>[^"]*)"(?: (?P<rt>[\d.]+))?'
)


@dataclass(frozen=True)
class Request:
    ip: str
    method: str
    path: str
    status: int
    size: int
    request_time: float | None


def parse_line(line: str) -> Request | None:
    m = LINE_RE.match(line)
    if not m:
        return None
    return Request(m["ip"], m["method"], m["path"], int(m["status"]),
                   0 if m["size"] == "-" else int(m["size"]),
                   float(m["rt"]) if m["rt"] else None)


def report(requests: list[Request], top: int, slow: float) -> dict:
    statuses = Counter(r.status for r in requests)
    return {
        "total": len(requests),
        "status_counts": sorted(statuses.items()),
        "error_5xx_percent": round(100 * sum(n for s, n in statuses.items() if s >= 500) / len(requests), 1),
        "top_ips": Counter(r.ip for r in requests).most_common(top),
        "top_404_paths": Counter(r.path for r in requests if r.status == 404).most_common(top),
        "slow_paths": Counter(r.path for r in requests if r.request_time and r.request_time >= slow).most_common(top),
        "bytes_sent": sum(r.size for r in requests),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Summarize an Nginx combined access log.")
    p.add_argument("log", type=Path)
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--slow", type=float, default=1.0, help="slow threshold in seconds")
    args = p.parse_args(argv)
    try:
        lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        print(f"error: file not found: {args.log}", file=sys.stderr)
        return 2
    requests = [r for r in map(parse_line, lines) if r]
    skipped = len([ln for ln in lines if ln.strip()]) - len(requests)
    if not requests:
        print("error: no parsable lines", file=sys.stderr)
        return 2
    rep = report(requests, args.top, args.slow)
    print(f"requests: {rep['total']}  (unparsable: {skipped})  bytes sent: {rep['bytes_sent']}")
    print("status codes: " + "  ".join(f"{s}={n}" for s, n in rep["status_counts"]))
    print(f"5xx error rate: {rep['error_5xx_percent']}%")
    for title, key in (("top client IPs", "top_ips"), ("top 404 paths", "top_404_paths"),
                       (f"slow paths (>= {args.slow:g}s)", "slow_paths")):
        print(f"{title}:")
        for value, n in rep[key]:
            print(f"  {n:>5}  {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
