#!/usr/bin/env python3
"""systemd service unit linter — best practice ও hardening যাচাই (static, read-only)।

এটি `systemd-analyze verify` (syntax/semantic) বা `systemd-analyze security` (exposure score)-এর
বিকল্প নয়; শেখার জন্য একটি ছোট, ব্যাখ্যাযোগ্য checklist।

Usage:
  python3 unit_lint.py taskflow-demo.service
  python3 unit_lint.py /etc/systemd/system/*.service
Exit: 0 = কোনো ERROR/WARN নেই, 1 = আছে, 2 = input error
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HARDENING = {
    "NoNewPrivileges": "setuid দিয়ে privilege বাড়ানো বন্ধ করে",
    "PrivateTmp": "নিজস্ব /tmp — অন্যদের file দেখা/বদলানো যায় না",
    "ProtectSystem": "/usr, /etc read-only (strict হলে প্রায় সব)",
    "ProtectHome": "/home ও /root লুকানো",
}


def parse_unit(text: str) -> dict[str, dict[str, list[str]]]:
    """INI-জাতীয়, কিন্তু একই key একাধিকবার থাকতে পারে (যেমন Environment=)।"""
    sections: dict[str, dict[str, list[str]]] = {}
    current = None
    pending = ""
    for raw in text.splitlines():
        line = raw.strip()
        if pending:
            line = pending + line
            pending = ""
        if line.endswith("\\"):
            pending = line[:-1].rstrip() + " "  # '\' আগের space বাদ, ঠিক একটি space রাখা
            continue
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, {})
            continue
        if current is None or "=" not in line:
            raise ValueError(f"invalid line outside section or without '=': {raw!r}")
        key, _, value = line.partition("=")
        sections[current].setdefault(key.strip(), []).append(value.strip())
    return sections


def last(sec: dict[str, list[str]], key: str) -> str | None:
    values = sec.get(key)
    return values[-1] if values else None  # পরের মান আগেরটিকে override করে (বেশিরভাগ key-তে)


def lint(text: str) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    u = parse_unit(text)
    unit, svc, inst = u.get("Unit", {}), u.get("Service"), u.get("Install", {})
    if not last(unit, "Description"):
        findings.append(("WARN", "[Unit] Description missing — systemctl status-এ অর্থবহ নাম দেখায় না"))
    if svc is None:
        return findings + [("ERROR", "no [Service] section")]
    exec_start = last(svc, "ExecStart")
    if not exec_start:
        findings.append(("ERROR", "[Service] ExecStart missing"))
    else:
        cmd = exec_start.lstrip("-@:+!")  # systemd prefix চিহ্ন বাদ
        prog = cmd.split()[0]
        if not prog.startswith("/"):
            findings.append(("WARN", f"ExecStart uses relative program '{prog}' — absolute path দিন"))
        if prog.endswith(("/sh", "/bash")) and " -c " in f" {cmd} " and "exec " not in cmd:
            findings.append(("WARN", "ExecStart runs a shell wrapper without 'exec' — SIGTERM child-এ না-ও পৌঁছাতে পারে"))
    user = last(svc, "User")
    if not user and last(svc, "DynamicUser") != "yes":
        findings.append(("WARN", "no User= — service root হিসেবে চলবে"))
    elif user == "root":
        findings.append(("WARN", "User=root — সত্যিই দরকার? least privilege"))
    restart = last(svc, "Restart")
    if not restart or restart == "no":
        findings.append(("WARN", "Restart= not set — crash-এর পরে service নিজে চালু হবে না"))
    if (last(svc, "Type") or "simple") == "forking" and not last(svc, "PIDFile"):
        findings.append(("WARN", "Type=forking without PIDFile= — main process চিনতে ভুল হতে পারে"))
    if not last(svc, "MemoryMax") and not last(svc, "MemoryHigh"):
        findings.append(("INFO", "no MemoryMax= — একটি leak পুরো server-এর memory নিতে পারে (L01-09)"))
    for key, why in HARDENING.items():
        value = last(svc, key)
        if not value or value in ("no", "false"):
            findings.append(("INFO", f"consider {key}= — {why}"))
    if not inst.get("WantedBy") and not inst.get("RequiredBy"):
        findings.append(("WARN", "[Install] WantedBy missing — systemctl enable কাজ করবে না"))
    return findings


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Lint systemd service units.")
    p.add_argument("units", nargs="+", type=Path)
    args = p.parse_args(argv)
    bad = False
    for path in args.units:
        try:
            findings = lint(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError) as exc:
            print(f"{path}: error: {exc}", file=sys.stderr)
            return 2
        print(f"{path.name}: {len(findings)} finding(s)")
        for level, msg in findings:
            print(f"  {level:5} {msg}")
        bad |= any(level in ("ERROR", "WARN") for level, _ in findings)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
