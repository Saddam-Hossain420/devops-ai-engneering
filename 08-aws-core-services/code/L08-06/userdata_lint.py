#!/usr/bin/env python3
"""userdata_lint.py — EC2 user data-র ঝুঁকি: secret (L05-10-এর scanner), আকার, interpreter, `set -e`, `curl | sh`।

  python3 userdata_lint.py user-data.sh

কেন secret নয়: user data instance-এর ভেতরে যেকোনো process IMDS থেকে পড়তে পারে, এবং ec2:DescribeInstanceAttribute
অনুমতি থাকা যে কেউ API দিয়ে — এটা encrypted নয়। Secret-এর জায়গা Secrets Manager/SSM Parameter Store (role দিয়ে পড়া)।
Exit: 0 কোনো ERROR নেই, 1 ERROR আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "05-python-for-infrastructure" / "code" / "L05-10"))
import scan_secrets  # noqa: E402

LIMIT = 16 * 1024
# L05-10-এর `assignment` নিয়ম শুধু quote-এর ভেতরের মান ধরে; shell-এ `export DB_PASSWORD=hunter2…` সাধারণত quote ছাড়া
SHELL_SECRET = re.compile(r"(?i)^\s*(?:export\s+)?(\w*(?:password|passwd|secret|token|api_?key)\w*)=([^\s\"'$]{8,})")
PIPE_TO_SHELL = re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh\b")


def lint(text: str, name: str = "user-data") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    size = len(text.encode())
    if size > LIMIT:
        out.append(("ERROR", f"{size} bytes — EC2 user data limit is {LIMIT} (before base64)"))
    first = text.splitlines()[0] if text else ""
    if not (first.startswith("#!") or first.startswith("#cloud-config")):
        out.append(("ERROR", "first line is neither a #! interpreter nor #cloud-config — cloud-init will not run it"))
    if first.startswith("#!") and "bash" in first and not re.search(r"^\s*set -[a-z]*e", text, re.M):
        out.append(("WARN", "no `set -e` — a failed step is ignored and the instance looks healthy but is half set up"))
    for f in scan_secrets.scan_text(text, name):
        out.append(("ERROR", f"line {f.line}: possible secret ({f.rule}) — user data is readable via IMDS and the API"))
    for n, line in enumerate(text.splitlines(), 1):
        m = SHELL_SECRET.match(line)
        if m and scan_secrets.INLINE_ALLOW not in line:
            out.append(("ERROR", f"line {n}: {m.group(1)} assigned a literal value — fetch it at boot from "
                                 "Secrets Manager/SSM Parameter Store instead"))
    for m in PIPE_TO_SHELL.finditer(text):
        line = text.count("\n", 0, m.start()) + 1
        out.append(("WARN", f"line {line}: download piped into a shell — pin a version and verify a checksum"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint EC2 user data.")
    ap.add_argument("file", type=Path)
    a = ap.parse_args(argv)
    try:
        text = a.file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = lint(text, a.file.name)
    for lvl, msg in findings:
        print(f"{lvl:<5}  {msg}")
    print(f"{a.file.name}: {len(text.encode())} bytes, {len(findings)} finding(s)")
    return 1 if any(lvl == "ERROR" for lvl, _ in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
