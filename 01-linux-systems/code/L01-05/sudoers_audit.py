#!/usr/bin/env python3
"""sudoers audit — ঝুঁকিপূর্ণ sudo নিয়ম খুঁজে বের করে (read-only, static analysis)।

এটি `visudo -c`-এর বিকল্প নয় (সেটি syntax যাচাই করে); এটি *নীতি* যাচাই করে:
  CRITICAL  NOPASSWD সহ ALL command
  HIGH      যেকোনো ALL command (পূর্ণ root)
  HIGH      shell escape সম্ভব এমন program (vi, less, find, python, bash ...)
  HIGH      command-এ wildcard (*) — argument দিয়ে নিয়ম এড়ানো যায়
  MEDIUM    absolute path ছাড়া command
  MEDIUM    NOPASSWD (নির্দিষ্ট command-এ — কারণ নথিভুক্ত থাকা উচিত)
  HIGH      Defaults-এ env_reset বন্ধ বা LD_PRELOAD/LD_LIBRARY_PATH রাখা

Usage:
  sudo cat /etc/sudoers /etc/sudoers.d/* > /tmp/sudoers-all.txt   # root লাগে
  python3 sudoers_audit.py /tmp/sudoers-all.txt
Exit code: 0 = CRITICAL/HIGH নেই, 1 = আছে, 2 = input error
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

SHELL_ESCAPE = {"vi", "vim", "nano", "less", "more", "man", "find", "awk", "gawk", "python", "python3",
                "perl", "ruby", "bash", "sh", "zsh", "env", "tar", "git", "nmap", "ftp", "ssh", "su",
                "docker", "journalctl", "systemctl", "apt", "apt-get", "dnf", "cp", "tee", "chmod", "chown"}
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
RULE_RE = re.compile(r"^(?P<who>\S+)\s+(?P<hosts>[^=\s]+)\s*=\s*(?:\((?P<runas>[^)]*)\)\s*)?(?P<rest>.+)$")


@dataclass(frozen=True)
class Finding:
    severity: str
    line: int
    message: str


def join_continuations(text: str) -> list[tuple[int, str]]:
    """'\\' দিয়ে শেষ হওয়া লাইন পরের লাইনের সাথে জোড়া; (শুরুর লাইন নম্বর, লাইন)।"""
    out, buf, start = [], "", 0
    for n, raw in enumerate(text.splitlines(), start=1):
        if not buf:
            start = n
        line = raw.rstrip()
        if line.endswith("\\"):
            buf += line[:-1] + " "
            continue
        out.append((start, buf + line))
        buf = ""
    if buf:
        out.append((start, buf))
    return out


def split_commands(rest: str) -> tuple[list[str], list[str]]:
    """'NOPASSWD: /usr/bin/systemctl restart nginx, /bin/ls' → (tags, commands)."""
    tags = []
    while True:
        m = re.match(r"^\s*([A-Z_]+):\s*", rest)
        if not m:
            break
        tags.append(m.group(1))
        rest = rest[m.end():]
    return tags, [c.strip() for c in rest.split(",") if c.strip()]


def audit(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in join_continuations(text):
        line = line.strip()
        if not line or (line.startswith("#") and not line.startswith(("#include", "#includedir"))):
            continue
        if line.startswith(("#include", "@include")):
            continue
        if line.startswith("Defaults"):
            if "!env_reset" in line:
                findings.append(Finding("HIGH", lineno, "env_reset disabled — caller's environment reaches root"))
            if re.search(r"env_keep\s*\+?=.*\b(LD_PRELOAD|LD_LIBRARY_PATH|PYTHONPATH)\b", line):
                findings.append(Finding("HIGH", lineno, "env_keep includes a library/loader variable"))
            continue
        if re.match(r"^(User|Runas|Host|Cmnd)_Alias\b", line):
            continue
        m = RULE_RE.match(line)
        if not m:
            continue
        who = m["who"]
        tags, commands = split_commands(m["rest"])
        nopasswd = "NOPASSWD" in tags
        escape_reported: set[str] = set()  # একই লাইনে একই program-এর জন্য একবার
        for cmd in commands:
            prog = cmd.split()[0]
            base = prog.rsplit("/", 1)[-1]
            if prog == "ALL":
                sev = "CRITICAL" if nopasswd else "HIGH"
                findings.append(Finding(sev, lineno, f"{who}: full root via ALL{' without password' if nopasswd else ''}"))
                continue
            if not prog.startswith("/"):
                findings.append(Finding("MEDIUM", lineno, f"{who}: command without absolute path: {prog}"))
            if re.sub(r"\d+(\.\d+)*$", "", base) in SHELL_ESCAPE and base not in escape_reported:
                escape_reported.add(base)
                findings.append(Finding("HIGH", lineno, f"{who}: {base} can spawn a shell or write files as root"))
            if "*" in cmd:
                findings.append(Finding("HIGH", lineno, f"{who}: wildcard in '{cmd}' can be abused with extra arguments"))
            if nopasswd:
                findings.append(Finding("MEDIUM", lineno, f"{who}: NOPASSWD for '{cmd}' — document why"))
    return sorted(findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.line))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Policy audit for sudoers rules.")
    p.add_argument("sudoers_file", type=Path)
    args = p.parse_args(argv)
    try:
        findings = audit(args.sudoers_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: file not found: {args.sudoers_file}", file=sys.stderr)
        return 2
    for f in findings:
        print(f"{f.severity:8} line {f.line:<3} {f.message}")
    counts = {s: sum(f.severity == s for f in findings) for s in SEVERITY_ORDER}
    print("summary: " + "  ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if counts["CRITICAL"] or counts["HIGH"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
