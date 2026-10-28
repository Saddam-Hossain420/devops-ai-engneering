#!/usr/bin/env python3
"""fs_tools.py — disk পরিষ্কারের আগে তদন্ত: সবচেয়ে বড় file, পুরোনো file, directory-র আকার; atomic write।

  python3 fs_tools.py largest /var/log -n 10
  python3 fs_tools.py older-than /var/log/app --days 14 --pattern '*.gz'          # শুধু তালিকা (dry-run)
  python3 fs_tools.py older-than /var/log/app --days 14 --pattern '*.gz' --delete # সত্যিই মোছা
  python3 fs_tools.py du /var/lib -d 1

নিয়ম: symlink অনুসরণ করা হয় না; পড়ার অনুমতি না থাকলে সেই অংশ বাদ দিয়ে stderr-এ সতর্কতা;
মোছা default-এ বন্ধ, এবং শুধু regular file (directory কখনো নয়)।
Exit: 0 OK, 1 কিছু path পড়া/মোছা যায়নি, 2 argument/root error।
"""
from __future__ import annotations

import argparse
import fnmatch
import heapq
import os
import sys
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Entry:
    path: Path
    size: int
    mtime: float


class Walker:
    """os.scandir-ভিত্তিক walk — symlink অনুসরণ নয়, ত্রুটি জমা রাখে।"""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def files(self, root: Path, pattern: str = "*") -> Iterator[Entry]:
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    for de in it:
                        try:
                            if de.is_dir(follow_symlinks=False):
                                stack.append(Path(de.path))
                            elif de.is_file(follow_symlinks=False) and fnmatch.fnmatch(de.name, pattern):
                                st = de.stat(follow_symlinks=False)
                                yield Entry(Path(de.path), st.st_size, st.st_mtime)
                        except OSError as exc:
                            self.errors.append(f"{de.path}: {exc.strerror}")
            except OSError as exc:
                self.errors.append(f"{current}: {exc.strerror}")


def human(n: float) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    raise AssertionError("unreachable")


def largest(root: Path, n: int, walker: Walker) -> list[Entry]:
    return heapq.nlargest(n, walker.files(root), key=lambda e: e.size)   # সব file memory-তে নয়


def older_than(root: Path, days: float, pattern: str, walker: Walker, now: float | None = None) -> list[Entry]:
    cutoff = (now if now is not None else time.time()) - days * 86400
    return sorted((e for e in walker.files(root, pattern) if e.mtime < cutoff), key=lambda e: e.mtime)


def du(root: Path, depth: int, walker: Walker) -> dict[Path, int]:
    """প্রতিটি file-এর size তার `depth` স্তরের পূর্বপুরুষ directory-তে যোগ।"""
    totals: dict[Path, int] = {}
    for e in walker.files(root):
        rel = e.path.relative_to(root).parts[:-1]
        key = root.joinpath(*rel[:depth])
        totals[key] = totals.get(key, 0) + e.size
    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))


def atomic_write(path: Path, data: str, mode: int | None = None) -> None:
    """একই directory-তে temp file → fsync → os.replace: পাঠক কখনো অর্ধেক file দেখবে না।"""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        elif path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o7777)    # পুরোনো permission রাখা
        os.replace(tmp, path)                              # একই filesystem-এ atomic
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Investigate disk usage safely.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("largest")
    p.add_argument("root", type=Path)
    p.add_argument("-n", type=int, default=10)
    p = sub.add_parser("older-than")
    p.add_argument("root", type=Path)
    p.add_argument("--days", type=float, required=True)
    p.add_argument("--pattern", default="*")
    p.add_argument("--delete", action="store_true", help="actually delete (default: list only)")
    p = sub.add_parser("du")
    p.add_argument("root", type=Path)
    p.add_argument("-d", "--depth", type=int, default=1)
    args = ap.parse_args(argv)

    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2
    w = Walker()
    if args.cmd == "largest":
        for e in largest(args.root, args.n, w):
            print(f"{human(e.size):>8}  {e.path}")
    elif args.cmd == "du":
        for path, size in du(args.root, args.depth, w).items():
            print(f"{human(size):>8}  {path}")
    else:
        entries = older_than(args.root, args.days, args.pattern, w)
        total = sum(e.size for e in entries)
        verb = "deleting" if args.delete else "would delete"
        for e in entries:
            age = (time.time() - e.mtime) / 86400
            print(f"{verb}: {e.path} ({human(e.size)}, {age:.0f} days)")
            if args.delete:
                try:
                    e.path.unlink()
                except OSError as exc:
                    w.errors.append(f"{e.path}: {exc.strerror}")
        print(f"{len(entries)} files, {human(total)}" + ("" if args.delete else " (dry-run; use --delete)"))
    for err in w.errors:
        print(f"WARN {err}", file=sys.stderr)
    return 1 if w.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
