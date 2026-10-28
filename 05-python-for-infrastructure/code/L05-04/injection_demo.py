#!/usr/bin/env python3
"""injection_demo.py — একই "file নাম" shell string-এ বসালে কী হয়, আর list argument-এ কী হয়।

Payload নিরীহ (`echo INJECTED`); কিছু মোছে বা বদলায় না। bash লাগে (Git Bash / Linux)।
  python3 injection_demo.py
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys

NAME = "report.txt; echo INJECTED"          # ব্যবহারকারী বা API থেকে আসা "file নাম"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    bash = shutil.which("bash")
    if bash is None:
        print("bash not found; skipping demo")
        return 0
    print(f"input name: {NAME!r}\n")

    unsafe = subprocess.run([bash, "-c", f"echo processing {NAME}"], capture_output=True, text=True)
    print("1) shell string (f-string), যেমন shell=True:")
    print("   " + unsafe.stdout.replace("\n", "\n   ").rstrip())

    quoted = subprocess.run([bash, "-c", f"echo processing {shlex.quote(NAME)}"], capture_output=True, text=True)
    print("2) shell string + shlex.quote:")
    print("   " + quoted.stdout.rstrip())

    listed = subprocess.run([sys.executable, "-c", "import sys; print('processing', sys.argv[1])", NAME],
                            capture_output=True, text=True)
    print("3) list argument, shell নেই:")
    print("   " + listed.stdout.rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
