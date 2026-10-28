#!/usr/bin/env python3
"""ভুলে commit হওয়া merge conflict marker খোঁজা — pre-commit hook বা CI step হিসেবে।

  python3 conflict_markers.py $(git ls-files)
  git diff --cached --name-only | xargs python3 conflict_markers.py

`git diff --check`-ও marker ধরে, তবে শুধু diff-এর অংশে; এটি পুরো file দেখে।
Exit: 0 পরিষ্কার, 1 marker পাওয়া গেছে, 2 file পড়া যায়নি।
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Git-এর marker ঠিক ৭টি অক্ষর, লাইনের শুরুতে; "=======" একা থাকলে markdown heading-এর underline হতে পারে,
# তাই সেটি শুধু একটি খোলা "<<<<<<<"-এর পরে গণ্য।
OPEN = re.compile(r"^<{7}(?: |$)")
MID = re.compile(r"^={7}$")
BASE = re.compile(r"^\|{7}(?: |$)")     # diff3/zdiff3 style-এর base অংশ
CLOSE = re.compile(r"^>{7}(?: |$)")


def scan(text: str) -> list[tuple[int, str]]:
    found, inside = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if OPEN.match(line):
            inside = True
            found.append((n, line))
        elif inside and (MID.match(line) or BASE.match(line)):
            found.append((n, line))
        elif inside and CLOSE.match(line):
            inside = False
            found.append((n, line))
    return found


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Find leftover merge conflict markers.")
    ap.add_argument("files", nargs="*", type=Path)
    args = ap.parse_args(argv)
    bad, unreadable = 0, 0
    for f in args.files:
        try:
            data = f.read_bytes()
        except OSError as exc:
            print(f"error: {f}: {exc.strerror}", file=sys.stderr)
            unreadable += 1
            continue
        if b"\x00" in data[:8000]:          # binary file বাদ
            continue
        for n, line in scan(data.decode("utf-8", "replace")):
            print(f"{f}:{n}: {line[:60]}")
            bad += 1
    if unreadable:
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
