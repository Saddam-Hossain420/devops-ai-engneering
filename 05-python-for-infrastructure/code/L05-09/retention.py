#!/usr/bin/env python3
"""retention.py — backup file-এর GFS (grandfather-father-son) retention: কোনগুলো রাখা হবে, কোনগুলো মোছা যাবে।

  python3 retention.py /var/backups/db --daily 7 --weekly 4 --monthly 6          # শুধু পরিকল্পনা (dry-run)
  python3 retention.py /var/backups/db --daily 7 --weekly 4 --monthly 6 --delete

File-এর নাম: <prefix>-YYYYMMDDTHHMMZ.<ext>  (যেমন db-20261027T0300Z.sql.gz) — সময় নাম থেকে, mtime থেকে নয়।
নিয়ম: প্রতিটি বাকেটে (দিন / ISO সপ্তাহ / মাস) সবচেয়ে নতুন backup রাখা; সবচেয়ে নতুন backup সবসময় থাকে;
ভবিষ্যতের সময়ের backup (clock skew) কখনো মোছা হয় না; নাম না মেলা file ছোঁয়া হয় না।
Exit: 0 OK, 1 কিছু মোছা যায়নি, 2 argument error।
"""
from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

NAME = re.compile(r"^(?P<prefix>.+)-(?P<ts>\d{8}T\d{4}Z)\.[A-Za-z0-9.]+$")


@dataclass(frozen=True, order=True)
class Backup:
    taken: datetime
    path: Path


@dataclass
class Plan:
    keep: dict[Path, list[str]]          # path → কেন রাখা (daily/weekly/monthly/newest/future)
    delete: list[Path]
    ignored: list[Path]


def parse_name(name: str) -> datetime | None:
    m = NAME.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group("ts"), "%Y%m%dT%H%MZ").replace(tzinfo=UTC)
    except ValueError:                    # 20261332 — দেখতে ঠিক, আসলে অসম্ভব তারিখ
        return None


def _bucket_keepers(backups: list[Backup], key: Callable[[date], object], count: int) -> list[Backup]:
    """নতুন থেকে পুরোনো: প্রতিটি নতুন বাকেটের প্রথম (সবচেয়ে নতুন) backup — প্রথম `count`টি বাকেট পর্যন্ত।"""
    seen: list[object] = []
    keepers = []
    for b in backups:
        k = key(b.taken.date())
        if k not in seen:
            if len(seen) == count:
                break
            seen.append(k)
            keepers.append(b)
    return keepers


def plan(paths: Iterable[Path], now: datetime, daily: int = 7, weekly: int = 4, monthly: int = 6) -> Plan:
    backups, ignored = [], []
    for p in paths:
        taken = parse_name(p.name)
        if taken is None:
            ignored.append(p)
        else:
            backups.append(Backup(taken, p))
    backups.sort(reverse=True)                          # নতুন আগে
    keep: dict[Path, list[str]] = {}
    future = [b for b in backups if b.taken > now]
    past = [b for b in backups if b.taken <= now]
    for b in future:
        keep.setdefault(b.path, []).append("future")
    if past:
        keep.setdefault(past[0].path, []).append("newest")
    rules: list[tuple[str, Callable[[date], object], int]] = [
        ("daily", lambda d: d, daily),
        ("weekly", lambda d: d.isocalendar()[:2], weekly),   # (ISO বছর, সপ্তাহ) — ক্যালেন্ডার বছর নয়
        ("monthly", lambda d: (d.year, d.month), monthly),
    ]
    for reason, key, count in rules:
        for b in _bucket_keepers(past, key, count):
            keep.setdefault(b.path, []).append(reason)
    delete = [b.path for b in reversed(past) if b.path not in keep]   # পুরোনো আগে
    return Plan(keep, delete, ignored)


def main(argv: list[str] | None = None, now: datetime | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="GFS retention for timestamped backup files.")
    ap.add_argument("directory", type=Path)
    ap.add_argument("--daily", type=int, default=7)
    ap.add_argument("--weekly", type=int, default=4)
    ap.add_argument("--monthly", type=int, default=6)
    ap.add_argument("--delete", action="store_true", help="actually delete (default: plan only)")
    args = ap.parse_args(argv)
    if min(args.daily, args.weekly, args.monthly) < 0 or not args.directory.is_dir():
        print("error: counts must be >= 0 and directory must exist", file=sys.stderr)
        return 2
    files = [p for p in args.directory.iterdir() if p.is_file() and not p.is_symlink()]
    result = plan(files, now or datetime.now(UTC), args.daily, args.weekly, args.monthly)
    for path, reasons in sorted(result.keep.items(), key=lambda kv: kv[0].name):
        print(f"keep    {path.name}  ({', '.join(reasons)})")
    failed = 0
    for path in result.delete:
        if args.delete:
            try:
                path.unlink()
                print(f"deleted {path.name}")
            except OSError as exc:
                failed += 1
                print(f"FAILED  {path.name}: {exc.strerror}", file=sys.stderr)
        else:
            print(f"delete  {path.name}  (dry-run)")
    for path in result.ignored:
        print(f"ignore  {path.name}  (name does not match)", file=sys.stderr)
    print(f"summary: keep={len(result.keep)} delete={len(result.delete)} ignored={len(result.ignored)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
