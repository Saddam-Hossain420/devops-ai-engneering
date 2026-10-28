#!/usr/bin/env python3
"""Exit code-এর অর্থ — 0, 1, 2, 126, 127, 128+N (signal) ইত্যাদি।

Usage:
  python3 exit_code.py 0 1 126 127 130 137 143
  some_command; python3 exit_code.py $?
"""
from __future__ import annotations

import sys

# Linux x86-64-এর signal নম্বর (signal(7)) — ব্যাখ্যার জন্য প্রচলিতগুলো
SIGNALS = {1: "SIGHUP", 2: "SIGINT", 3: "SIGQUIT", 6: "SIGABRT", 9: "SIGKILL", 11: "SIGSEGV",
           13: "SIGPIPE", 14: "SIGALRM", 15: "SIGTERM"}
SIGNAL_MEANING = {
    "SIGHUP": "terminal বন্ধ বা reload অনুরোধ",
    "SIGINT": "Ctrl+C",
    "SIGQUIT": "Ctrl+\\ (core dump সহ)",
    "SIGABRT": "program নিজে abort করেছে",
    "SIGKILL": "জোর করে মারা — প্রায়ই OOM killer বা kill -9 / container memory limit",
    "SIGSEGV": "অবৈধ memory access (crash)",
    "SIGPIPE": "pipe-এর অন্য প্রান্ত বন্ধ (যেমন | head)",
    "SIGALRM": "timer",
    "SIGTERM": "ভদ্রভাবে বন্ধের অনুরোধ (systemctl stop, docker stop, kill)",
}


def explain(code: int) -> str:
    if not 0 <= code <= 255:
        return f"{code}: invalid — exit status 0-255 (shell শুধু নিচের ৮ bit রাখে: {code % 256})"
    if code == 0:
        return "0: success"
    if code == 1:
        return "1: general error (program-নির্দিষ্ট)"
    if code == 2:
        return "2: misuse / invalid arguments (অনেক tool-এর convention; Bash builtin-এর ভুল ব্যবহার)"
    if code == 126:
        return "126: command found but not executable (permission বা noexec)"
    if code == 127:
        return "127: command not found (PATH বা বানান)"
    if code > 128:
        sig = code - 128
        name = SIGNALS.get(sig, f"signal {sig}")
        meaning = SIGNAL_MEANING.get(name, "")
        return f"{code}: killed by {name} (128+{sig}){' — ' + meaning if meaning else ''}"
    return f"{code}: program-specific error (documentation দেখুন)"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: exit_code.py CODE [CODE ...]", file=sys.stderr)
        return 2
    for raw in args:
        try:
            print(explain(int(raw)))
        except ValueError:
            print(f"error: not an integer: {raw!r}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
