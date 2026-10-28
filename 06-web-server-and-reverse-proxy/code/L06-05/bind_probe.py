#!/usr/bin/env python3
"""bind_probe.py — একই port-এ দুটি process bind করলে কী হয়: OS-ভেদে আচরণ আসলে মেপে দেখা।

  python3 bind_probe.py

প্রতিটি case-এ প্রথম socket bind + listen, তারপর দ্বিতীয়টি bind-এর চেষ্টা — ফল print।
শুধু 127.0.0.1/0.0.0.0-এ, OS-নির্বাচিত খালি port-এ; কিছু চালু থাকে না।
"""
from __future__ import annotations

import os
import socket
import sys


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def try_pair(first: str, second: str, reuse: bool = False) -> str:
    port = free_port()
    a = socket.socket()
    b = socket.socket()
    try:
        if reuse:
            for s in (a, b):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        a.bind((first, port))
        a.listen()
        try:
            b.bind((second, port))
            b.listen()
            return "BOTH BOUND"
        except OSError as exc:
            return f"second failed: [{exc.errno}] {exc.strerror}"
    finally:
        a.close()
        b.close()


CASES = [
    ("127.0.0.1", "127.0.0.1", False),
    ("0.0.0.0", "127.0.0.1", False),
    ("127.0.0.1", "0.0.0.0", False),
    ("0.0.0.0", "127.0.0.1", True),
]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"platform: {sys.platform} ({os.name})")
    for first, second, reuse in CASES:
        label = f"{first:<9} then {second:<9}{' (SO_REUSEADDR)' if reuse else ''}"
        print(f"  {label:<44} → {try_pair(first, second, reuse)}")


if __name__ == "__main__":
    main()
