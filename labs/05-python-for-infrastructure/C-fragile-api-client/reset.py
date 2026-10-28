#!/usr/bin/env python3
"""Lab 05-C cleanup — শুধু `.lab05c` চিহ্নযুক্ত directory মোছে।   python3 reset.py ~/lab05c"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 reset.py DIR", file=sys.stderr)
        return 64
    dest = Path(sys.argv[1]).expanduser()
    if not (dest / ".lab05c").is_file():
        print(f"refusing: {dest} is not a Lab 05-C directory", file=sys.stderr)
        return 2
    shutil.rmtree(dest)
    print(f"removed {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
