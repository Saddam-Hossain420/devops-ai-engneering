#!/usr/bin/env python3
"""strace output summarizer — `strace -o trace.txt <command>` দিয়ে পাওয়া file থেকে
কোন system call কতবার, কোনগুলো ব্যর্থ (কোন errno) — তার সারাংশ।

Line format (strace default; -f থাকলে শুরুতে PID থাকতে পারে):
  openat(AT_FDCWD, "/etc/hosts", O_RDONLY|O_CLOEXEC) = 3
  12345 openat(AT_FDCWD, "/nope", O_RDONLY) = -1 ENOENT (No such file or directory)

Usage:
  strace -o /tmp/trace.txt cat /etc/hostname
  python3 strace_summary.py /tmp/trace.txt
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

LINE_RE = re.compile(
    r"^(?:(?P<pid>\d+)\s+)?(?P<name>[a-z_0-9]+)\((?P<args>.*)\)\s+=\s+(?P<ret>-?\d+|\?|0x[0-9a-f]+)"
    r"(?:\s+(?P<errno>E[A-Z]+))?"
)


@dataclass(frozen=True)
class Call:
    name: str
    ret: str
    errno: str | None
    args: str


def parse_line(line: str) -> Call | None:
    """'+++ exited', '--- SIGCHLD', '<unfinished ...>' জাতীয় লাইন None।"""
    m = LINE_RE.match(line.strip())
    if not m:
        return None
    return Call(m["name"], m["ret"], m["errno"], m["args"])


def summarize(calls: list[Call]) -> tuple[Counter, Counter, list[Call]]:
    counts = Counter(c.name for c in calls)
    errors = Counter((c.name, c.errno) for c in calls if c.errno)
    opened_files = [c for c in calls if c.name in ("open", "openat") and c.errno is None]
    return counts, errors, opened_files


def first_string_arg(args: str) -> str:
    m = re.search(r'"([^"]*)"', args)
    return m.group(1) if m else "?"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Summarize an strace output file.")
    p.add_argument("trace_file", type=Path)
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args(argv)
    try:
        lines = args.trace_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        print(f"error: file not found: {args.trace_file}", file=sys.stderr)
        return 2

    calls = [c for c in (parse_line(line) for line in lines) if c]
    if not calls:
        print("error: no system calls found — is this strace output?", file=sys.stderr)
        return 2
    counts, errors, opened = summarize(calls)

    print(f"total system calls: {len(calls)}   distinct: {len(counts)}")
    print("\nmost frequent:")
    for name, n in counts.most_common(args.top):
        print(f"  {n:>5}  {name}")
    print("\nfailed calls (name, errno):")
    for (name, errno), n in errors.most_common() or [(("none", ""), 0)]:
        print(f"  {n:>5}  {name} {errno}")
    print("\nfiles opened successfully:")
    for c in opened[: args.top]:
        print(f"  fd={c.ret:>3}  {first_string_arg(c.args)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
