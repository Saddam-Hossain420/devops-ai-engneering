#!/usr/bin/env python3
"""Boot ও update স্বাস্থ্য — boot সময় বিশ্লেষণ এবং reboot দরকার কিনা (read-only)।

Input (read-only command):
  systemd-analyze > analyze.txt
  systemd-analyze blame > blame.txt
  uname -r > running.txt
  ls /boot/vmlinuz-* > kernels.txt
  cat /var/run/reboot-required.pkgs > pkgs.txt   # Ubuntu, না থাকলে খালি

Usage:
  python3 boot_report.py boot analyze.txt blame.txt --top 5
  python3 boot_report.py reboot --running running.txt --kernels kernels.txt [--pkgs pkgs.txt]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TIME_RE = re.compile(r"(?:(\d+)min\s*)?(?:(\d+(?:\.\d+)?)s)?(?:(\d+)ms)?")


def to_seconds(text: str) -> float:
    """'1min 2.345s', '6.401s', '812ms', '2min 3s' → সেকেন্ড।"""
    text = text.strip()
    m = TIME_RE.fullmatch(text.replace(" ", ""))
    if not m or not any(m.groups()):
        raise ValueError(f"cannot parse duration {text!r}")
    minutes, seconds, ms = m.groups()
    return int(minutes or 0) * 60 + float(seconds or 0) + int(ms or 0) / 1000


def parse_analyze(text: str) -> dict[str, float]:
    """'Startup finished in 3.2s (firmware) + 2.1s (loader) + 1.8s (kernel) + 6.4s (userspace) = 13.6s'."""
    m = re.search(r"Startup finished in (.+?) = ([^\n]+)", text)
    if not m:
        raise ValueError("no 'Startup finished' line — boot এখনো শেষ হয়নি বা format আলাদা")
    phases = {}
    for part in m.group(1).split(" + "):
        pm = re.match(r"(.+?) \((\w[\w-]*)\)", part.strip())
        if pm:
            phases[pm.group(2)] = to_seconds(pm.group(1))
    phases["total"] = to_seconds(m.group(2))  # যেমন '1min 13.552s'
    return phases


def parse_blame(text: str) -> list[tuple[float, str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        duration, _, unit = line.rpartition(" ")
        try:
            rows.append((to_seconds(duration), unit))
        except ValueError:
            continue
    return sorted(rows, reverse=True)


def version_key(v: str) -> list:
    """'6.8.0-45-generic' → [6, 8, 0, 45, 'generic'] — সংখ্যা সংখ্যা হিসেবে তুলনা।"""
    return [int(x) if x.isdigit() else x for x in re.split(r"[.\-+]", v)]


def kernel_versions(listing: str) -> list[str]:
    """'/boot/vmlinuz-6.8.0-45-generic' লাইনগুলো থেকে version (Fedora: vmlinuz-6.11.4-301.fc41.x86_64)।"""
    out = []
    for line in listing.split():
        name = line.rsplit("/", 1)[-1]
        if name.startswith("vmlinuz-") and "rescue" not in name:
            out.append(name[len("vmlinuz-"):])
    return sorted(set(out), key=version_key)


def reboot_needed(running: str, installed: list[str], pkgs: list[str]) -> tuple[bool, list[str]]:
    reasons = []
    if installed and installed[-1] != running:
        reasons.append(f"newer kernel installed: {installed[-1]} (running {running})")
    if running not in installed:
        reasons.append(f"running kernel {running} no longer installed in /boot")
    if pkgs:
        reasons.append(f"packages requesting reboot: {', '.join(pkgs)}")
    return bool(reasons), reasons


def read(path: Path | None) -> str:
    return path.read_text(encoding="utf-8") if path else ""


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Boot timing and reboot-needed report.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("boot")
    b.add_argument("analyze", type=Path)
    b.add_argument("blame", type=Path)
    b.add_argument("--top", type=int, default=5)
    r = sub.add_parser("reboot")
    r.add_argument("--running", type=Path, required=True)
    r.add_argument("--kernels", type=Path, required=True)
    r.add_argument("--pkgs", type=Path)
    args = p.parse_args(argv)

    try:
        if args.cmd == "boot":
            phases = parse_analyze(read(args.analyze))
            total = phases.pop("total")
            print(f"total boot: {total:.1f}s")
            for name, sec in phases.items():
                print(f"  {name:10} {sec:6.1f}s  {100 * sec / total:5.1f}%")
            print(f"slowest units (top {args.top}):")
            for sec, unit in parse_blame(read(args.blame))[: args.top]:
                print(f"  {sec:6.2f}s  {unit}")
        else:
            running = read(args.running).strip()
            installed = kernel_versions(read(args.kernels))
            pkgs = [x for x in read(args.pkgs).split() if x]
            needed, reasons = reboot_needed(running, installed, pkgs)
            print(f"running kernel  : {running}")
            print(f"installed       : {', '.join(installed) or '(none found)'}")
            print(f"reboot needed   : {'YES' if needed else 'no'}")
            for reason in reasons:
                print(f"  - {reason}")
            return 1 if needed else 0
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
