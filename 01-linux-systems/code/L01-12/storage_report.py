#!/usr/bin/env python3
"""Storage report — lsblk tree, LVM capacity ও disk-full forecast (read-only)।

Input তৈরি (read-only command):
  lsblk -J -b -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS > lsblk.json
  sudo vgs --reportformat json --units b --nosuffix -o vg_name,vg_size,vg_free > vgs.json
  sudo lvs --reportformat json --units b --nosuffix -o lv_name,vg_name,lv_size > lvs.json

Usage:
  python3 storage_report.py lsblk lsblk.json
  python3 storage_report.py lvm vgs.json lvs.json
  python3 storage_report.py forecast --size-gb 50 --used-gb 41 --growth-gb-per-day 0.6
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path


def human(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024 or unit == "TiB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def lsblk_tree(data: dict) -> list[str]:
    lines: list[str] = []

    def walk(dev: dict, prefix: str, last: bool, depth: int) -> None:
        mounts = [m for m in (dev.get("mountpoints") or [dev.get("mountpoint")]) if m]
        branch = "" if depth == 0 else ("└─" if last else "├─")
        label = f"{prefix}{branch}{dev['name']}"  # prefix সহ মোট প্রস্থ ঠিক রাখলে column সোজা থাকে
        lines.append(f"{label:<26} {human(int(dev['size'])):>10}  {dev['type']:<5} "
                     f"{dev.get('fstype') or '-':<12} {','.join(mounts) or '-'}")
        kids = dev.get("children", [])
        for i, k in enumerate(kids):
            walk(k, prefix + ("" if depth == 0 else ("  " if last else "│ ")), i == len(kids) - 1, depth + 1)

    for d in data["blockdevices"]:
        walk(d, "", True, 0)
    return lines


def lvm_report(vgs: dict, lvs: dict) -> tuple[list[str], list[str]]:
    vg_rows = vgs["report"][0]["vg"]
    lv_rows = lvs["report"][0]["lv"]
    lines, warnings = [], []
    for vg in vg_rows:
        size, free = int(vg["vg_size"]), int(vg["vg_free"])
        pct = 100 * free / size if size else 0
        lines.append(f"VG {vg['vg_name']}: size {human(size)}, free {human(free)} ({pct:.1f}%)")
        for lv in (lv for lv in lv_rows if lv["vg_name"] == vg["vg_name"]):
            lines.append(f"  LV {lv['lv_name']:<12} {human(int(lv['lv_size']))}")
        if pct < 10:
            warnings.append(f"VG {vg['vg_name']} has <10% free — নতুন disk (PV) যোগ বা LV ছোট করার পরিকল্পনা করুন")
    return lines, warnings


def days_until_full(size_gb: float, used_gb: float, growth_per_day: float, threshold: float = 1.0) -> float:
    """বর্তমান হারে threshold (যেমন 0.9 = ৯০%) পর্যন্ত পৌঁছাতে কত দিন। বৃদ্ধি ০ হলে inf।"""
    if size_gb <= 0 or not 0 <= used_gb <= size_gb:
        raise ValueError("need 0 <= used <= size and size > 0")
    remaining = size_gb * threshold - used_gb
    if remaining <= 0:
        return 0.0
    if growth_per_day <= 0:
        return math.inf
    return remaining / growth_per_day


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Storage report: lsblk, LVM, forecast.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("lsblk").add_argument("file", type=Path)
    lv = sub.add_parser("lvm")
    lv.add_argument("vgs", type=Path)
    lv.add_argument("lvs", type=Path)
    f = sub.add_parser("forecast")
    f.add_argument("--size-gb", type=float, required=True)
    f.add_argument("--used-gb", type=float, required=True)
    f.add_argument("--growth-gb-per-day", type=float, required=True)
    args = p.parse_args(argv)

    try:
        if args.cmd == "lsblk":
            for line in lsblk_tree(json.loads(args.file.read_text(encoding="utf-8"))):
                print(line)
        elif args.cmd == "lvm":
            lines, warns = lvm_report(json.loads(args.vgs.read_text(encoding="utf-8")),
                                      json.loads(args.lvs.read_text(encoding="utf-8")))
            for line in lines + [f"WARN {w}" for w in warns]:
                print(line)
            return 1 if warns else 0
        else:
            for label, th in (("80% (warning)", 0.8), ("90% (critical)", 0.9), ("100% (full)", 1.0)):
                d = days_until_full(args.size_gb, args.used_gb, args.growth_gb_per_day, th)
                text = "never at this rate" if math.isinf(d) else ("already reached" if d == 0 else f"{d:.1f} days")
                print(f"reach {label:15}: {text}")
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
