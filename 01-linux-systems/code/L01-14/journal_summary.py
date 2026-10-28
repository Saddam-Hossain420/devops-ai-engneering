#!/usr/bin/env python3
"""journalctl JSON summary — কোন unit কত log, কোন priority, শীর্ষ error ও সময়সীমা।

Input (read-only):
  journalctl -o json --since "1 hour ago" > journal.jsonl
  (প্রতি লাইনে একটি JSON object; journald-এর field: PRIORITY, _SYSTEMD_UNIT, MESSAGE ...)

Usage:
  python3 journal_summary.py journal.jsonl
  python3 journal_summary.py journal.jsonl --max-priority 3     # শুধু err ও তার চেয়ে গুরুতর
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# syslog priority (RFC 5424): ছোট সংখ্যা = বেশি গুরুতর
PRIORITY_NAMES = ["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]


@dataclass(frozen=True)
class Entry:
    time: datetime
    priority: int
    source: str
    message: str


def parse_line(line: str) -> Entry | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    ts = int(obj.get("__REALTIME_TIMESTAMP", "0"))  # epoch থেকে microsecond
    msg = obj.get("MESSAGE", "")
    if isinstance(msg, list):  # journald binary/non-UTF-8 message-কে byte array হিসেবে দেয়
        msg = bytes(msg).decode("utf-8", errors="replace")
    source = obj.get("_SYSTEMD_UNIT") or obj.get("SYSLOG_IDENTIFIER") or "unknown"
    return Entry(datetime.fromtimestamp(ts / 1_000_000, tz=timezone.utc),
                 int(obj.get("PRIORITY", 6)), source, msg)


def summarize(entries: list[Entry], max_priority: int) -> dict:
    selected = [e for e in entries if e.priority <= max_priority]
    return {
        "total": len(entries),
        "selected": len(selected),
        "first": min(e.time for e in entries) if entries else None,
        "last": max(e.time for e in entries) if entries else None,
        "by_priority": Counter(PRIORITY_NAMES[e.priority] for e in entries),
        "by_source": Counter(e.source for e in selected),
        "top_messages": Counter((e.source, e.message) for e in selected).most_common(5),
        "worst": min(selected, key=lambda e: (e.priority, e.time)) if selected else None,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Summarize journalctl -o json output.")
    p.add_argument("file", type=Path)
    p.add_argument("--max-priority", type=int, default=4, choices=range(8),
                   help="include priority <= N (default 4 = warning and worse)")
    args = p.parse_args(argv)
    try:
        lines = args.file.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    entries = [e for e in map(parse_line, lines) if e]
    skipped = sum(1 for ln in lines if ln.strip()) - len(entries)
    if not entries:
        print("error: no journal entries", file=sys.stderr)
        return 2
    s = summarize(entries, args.max_priority)
    print(f"entries: {s['total']} (skipped {skipped})  window: {s['first']:%H:%M:%S} → {s['last']:%H:%M:%S} UTC")
    print("by priority: " + "  ".join(f"{n}={s['by_priority'][n]}" for n in PRIORITY_NAMES if s["by_priority"][n]))
    print(f"\npriority <= {args.max_priority} ({PRIORITY_NAMES[args.max_priority]}): {s['selected']} entries")
    for src, n in s["by_source"].most_common():
        print(f"  {n:>4}  {src}")
    print("top messages:")
    for (src, msg), n in s["top_messages"]:
        print(f"  {n:>4}  [{src}] {msg}")
    if s["worst"]:
        w = s["worst"]
        print(f"most severe: {PRIORITY_NAMES[w.priority]} at {w.time:%H:%M:%S} [{w.source}] {w.message}")
    return 1 if any(e.priority <= 3 for e in entries) else 0


if __name__ == "__main__":
    raise SystemExit(main())
