#!/usr/bin/env python3
"""Cron expression ব্যাখ্যা — পরের N বার কখন চলবে, এবং systemd OnCalendar-এ রূপান্তর।

Format (৫ field): minute hour day-of-month month day-of-week
  *        যেকোনো
  5        নির্দিষ্ট মান
  1-5      পরিসর
  */15     প্রতি ১৫ (শুরু থেকে)
  1,15,30  তালিকা
  day-of-week: 0 বা 7 = রবিবার, 1 = সোমবার ... 6 = শনিবার

নিয়ম (cron-এর আসল আচরণ): day-of-month ও day-of-week দুটোই '*' না হলে —
যেকোনো একটি মিললেই চলে (OR), দুটো একসাথে (AND) নয়।

Usage:
  python3 cron_explain.py "*/15 9-17 * * 1-5" --count 5 --start 2026-10-26T08:50
  python3 cron_explain.py "30 2 * * 0"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

FIELDS = (("minute", 0, 59), ("hour", 0, 23), ("day", 1, 31), ("month", 1, 12), ("weekday", 0, 7))
DOW_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]


def parse_field(text: str, low: int, high: int) -> set[int]:
    values: set[int] = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/", 1)
            step = int(step_text)
            if step < 1:
                raise ValueError(f"invalid step in {text!r}")
        if part == "*":
            start, end = low, high
        elif "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
        else:
            start = int(part)
            end = high if step > 1 else start  # "5/10" = ৫ থেকে প্রতি ১০
        if not (low <= start <= high and low <= end <= high and start <= end):
            raise ValueError(f"value out of range {low}-{high} in {text!r}")
        values.update(range(start, end + 1, step))
    return values


class Cron:
    def __init__(self, expr: str) -> None:
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError(f"expected 5 fields, got {len(parts)}: {expr!r}")
        self.raw = parts
        sets = [parse_field(p, lo, hi) for p, (_, lo, hi) in zip(parts, FIELDS)]
        self.minutes, self.hours, self.days, self.months, dows = sets
        self.dows = {d % 7 for d in dows}  # 7 → 0 (রবিবার)
        self.dom_any = parts[2] == "*"
        self.dow_any = parts[4] == "*"

    def matches(self, t: datetime) -> bool:
        if t.minute not in self.minutes or t.hour not in self.hours or t.month not in self.months:
            return False
        dow = (t.weekday() + 1) % 7  # Python: Mon=0 → cron: Mon=1, Sun=0
        dom_ok, dow_ok = t.day in self.days, dow in self.dows
        if self.dom_any and self.dow_any:
            return True
        if self.dom_any:
            return dow_ok
        if self.dow_any:
            return dom_ok
        return dom_ok or dow_ok  # cron-এর OR নিয়ম

    def next_runs(self, start: datetime, count: int, horizon_days: int = 1500) -> list[datetime]:
        t = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
        end = start + timedelta(days=horizon_days)
        runs: list[datetime] = []
        while len(runs) < count and t <= end:
            if self.matches(t):
                runs.append(t)
            t += timedelta(minutes=1)
        return runs


def to_oncalendar(expr: str) -> str:
    """সাধারণ ক্ষেত্রে systemd OnCalendar=; জটিল/OR ক্ষেত্রে ব্যাখ্যাসহ সতর্কতা।"""
    minute, hour, dom, month, dow = expr.split()
    if dom != "*" and dow != "*":
        return "(manual) dom ও dow দুটোই দেওয়া — cron OR করে, OnCalendar AND করে; দুটি আলাদা timer লিখুন"

    def conv(field: str, width: int) -> str:
        if field == "*":
            return "*"
        if field.startswith("*/"):
            return f"00/{field[2:]}" if width == 2 else f"*/{field[2:]}"
        return ",".join(f"{int(x):0{width}d}" if x.isdigit() else x.replace("-", "..") for x in field.split(","))

    days = ""
    if dow != "*":
        names = []
        for part in dow.split(","):
            if "-" in part:
                a, b = (int(x) % 7 for x in part.split("-"))
                names.append(f"{DOW_NAMES[a]}..{DOW_NAMES[b]}")
            else:
                names.append(DOW_NAMES[int(part) % 7])
        days = ",".join(names) + " "
    return f"{days}*-{conv(month, 2)}-{conv(dom, 2)} {conv(hour, 2)}:{conv(minute, 2)}:00"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Explain a cron expression.")
    p.add_argument("expr")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--start", type=datetime.fromisoformat, default=None, help="YYYY-MM-DDTHH:MM")
    args = p.parse_args(argv)
    try:
        cron = Cron(args.expr)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    start = args.start or datetime.now()
    print(f"cron      : {args.expr}")
    print(f"OnCalendar: {to_oncalendar(args.expr)}")
    print(f"next {args.count} run(s) after {start:%Y-%m-%d %H:%M}:")
    for t in cron.next_runs(start, args.count):
        print(f"  {t:%a %Y-%m-%d %H:%M}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
