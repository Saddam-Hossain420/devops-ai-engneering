#!/usr/bin/env python3
"""System call demo — একটি জানা ক্রমে low-level file operation করে, যাতে strace দিয়ে
প্রতিটি Python লাইনের পেছনের system call দেখা যায়।

`os.open`, `os.write` ইত্যাদি প্রায় সরাসরি kernel-এর system call-এর পাতলা wrapper।
Script একটি temporary directory-তে কাজ করে এবং শেষে সব মুছে ফেলে।

Usage:
  python3 syscall_demo.py
  strace -f -e trace=openat,write,fsync,close,newfstatat,unlink,getpid python3 syscall_demo.py
"""
from __future__ import annotations

import os
import sys
import tempfile


def demo(directory: str) -> list[str]:
    """প্রতিটি ধাপের বর্ণনা ফেরত দেয় (test-এর জন্য)।"""
    steps: list[str] = []
    path = os.path.join(directory, "demo.txt")

    pid = os.getpid()                                       # getpid()
    steps.append(f"getpid -> {pid}")

    # O_BINARY শুধু Windows-এ আছে: সেখানে default text mode "\n"-কে "\r\n" করে দেয়।
    # Linux-এ text/binary পার্থক্য নেই, তাই getattr(..., 0) সেখানে কিছু বদলায় না।
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags, 0o600)                        # openat()
    steps.append(f"open -> file descriptor {fd}")

    written = os.write(fd, b"hello kernel\n")               # write()
    steps.append(f"write -> {written} bytes")

    os.fsync(fd)                                            # fsync(): disk-এ পৌঁছানো নিশ্চিত
    steps.append("fsync -> data flushed to storage")

    os.close(fd)                                            # close()
    steps.append("close -> fd released")

    size = os.stat(path).st_size                            # newfstatat() / statx()
    steps.append(f"stat -> size {size}")

    try:
        os.open(os.path.join(directory, "missing.txt"), os.O_RDONLY)  # ব্যর্থ openat()
    except FileNotFoundError as exc:
        steps.append(f"open missing -> errno {exc.errno} ({os.strerror(exc.errno)})")

    os.unlink(path)                                         # unlink()
    steps.append("unlink -> file removed")
    return steps


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="syscall-demo-") as d:
        for step in demo(d):
            print(step)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
