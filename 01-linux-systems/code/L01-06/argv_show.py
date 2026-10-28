#!/usr/bin/env python3
"""Program আসলে কোন argument পেল তা দেখায় — shell quoting ও expansion বোঝার জন্য।

Shell command line-কে ভেঙে (word splitting), expand করে (variable, glob, ~),
quote সরিয়ে তারপর program-কে argument-এর তালিকা দেয়। এই script সেই তালিকা হুবহু দেখায়।

Usage (Bash-এ):
  python3 argv_show.py hello world
  python3 argv_show.py "hello world"
  name="my file.txt"; python3 argv_show.py $name "$name"
  python3 argv_show.py *.py '*.py'
"""
from __future__ import annotations

import sys


def describe(args: list[str]) -> list[str]:
    lines = [f"received {len(args)} argument(s)"]
    for i, a in enumerate(args, start=1):
        lines.append(f"  [{i}] {a!r}")  # repr: space, tab, খালি string স্পষ্ট দেখা যায়
    return lines


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for line in describe(sys.argv[1:]):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
