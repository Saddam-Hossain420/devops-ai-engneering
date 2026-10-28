#!/usr/bin/env python3
"""USE method checker — vmstat ও iostat -x output থেকে Utilization / Saturation / Errors table।

Input (read-only):
  vmstat 1 6 > vmstat.txt          # প্রথম লাইন boot থেকে গড় — বাদ দেওয়া হয়
  iostat -x 1 3 > iostat.txt       # sysstat; header-এর column নাম দিয়ে parse
Usage:
  python3 use_check.py --vmstat vmstat.txt --iostat iostat.txt --cpus 4
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path


def parse_vmstat(text: str) -> list[dict[str, int]]:
    """Header 'r b swpd free ...' খুঁজে প্রতিটি data লাইন dict-এ; প্রথম data লাইন (boot গড়) বাদ।"""
    rows: list[dict[str, int]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        parts = line.split()
        if parts[:2] == ["r", "b"]:
            header = parts
            continue
        if header and parts and parts[0].isdigit() and len(parts) == len(header):
            rows.append(dict(zip(header, map(int, parts))))
    return rows[1:] if len(rows) > 1 else rows


def parse_iostat(text: str) -> dict[str, list[dict[str, float]]]:
    """প্রতিটি 'Device ...' block; প্রথম block (boot গড়) বাদ।"""
    blocks: list[dict[str, dict[str, float]]] = []
    header: list[str] | None = None
    for line in text.splitlines():
        parts = line.split()
        if parts and parts[0].startswith("Device"):
            header = parts
            blocks.append({})
            continue
        if not parts:
            header = None
            continue
        if header and len(parts) == len(header):
            blocks[-1][parts[0]] = dict(zip(header[1:], map(float, parts[1:])))
    use = blocks[1:] if len(blocks) > 1 else blocks
    per_dev: dict[str, list[dict[str, float]]] = {}
    for b in use:
        for dev, vals in b.items():
            per_dev.setdefault(dev, []).append(vals)
    return per_dev


def verdict(value: float, warn: float, crit: float) -> str:
    return "CRIT" if value >= crit else ("WARN" if value >= warn else "ok")


def use_table(vm: list[dict[str, int]], io: dict[str, list[dict[str, float]]], cpus: int) -> list[tuple]:
    rows = []
    if vm:
        cpu_util = statistics.mean(100 - r["id"] for r in vm)
        runq = statistics.mean(r["r"] for r in vm)
        iowait = statistics.mean(r["wa"] for r in vm)
        swap = statistics.mean(r["si"] + r["so"] for r in vm)
        blocked = statistics.mean(r["b"] for r in vm)
        rows.append(("CPU", "utilization", f"{cpu_util:.0f}%", verdict(cpu_util, 70, 90)))
        rows.append(("CPU", "saturation (run queue/cpu)", f"{runq / cpus:.2f}", verdict(runq / cpus, 1.0, 2.0)))
        rows.append(("CPU", "iowait", f"{iowait:.0f}%", verdict(iowait, 10, 30)))
        rows.append(("Memory", "saturation (swap in+out)", f"{swap:.0f}/s", verdict(swap, 1, 100)))
        rows.append(("Tasks", "blocked in I/O (b)", f"{blocked:.1f}", verdict(blocked, 1, 4)))
    for dev, samples in sorted(io.items()):
        util = statistics.mean(s.get("%util", 0.0) for s in samples)
        queue = statistics.mean(s.get("aqu-sz", s.get("avgqu-sz", 0.0)) for s in samples)
        wait = statistics.mean(max(s.get("r_await", 0.0), s.get("w_await", 0.0)) for s in samples)
        rows.append((f"Disk {dev}", "utilization", f"{util:.0f}%", verdict(util, 60, 90)))
        rows.append((f"Disk {dev}", "saturation (queue)", f"{queue:.2f}", verdict(queue, 1, 4)))
        rows.append((f"Disk {dev}", "latency (max r/w await)", f"{wait:.1f} ms", verdict(wait, 20, 100)))
    rows.append(("Errors", "check separately", "dmesg/journalctl -k, ip -s link", "manual"))
    return rows


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="USE method table from vmstat/iostat output.")
    p.add_argument("--vmstat", type=Path)
    p.add_argument("--iostat", type=Path)
    p.add_argument("--cpus", type=int, required=True)
    args = p.parse_args(argv)
    if not args.vmstat and not args.iostat:
        p.error("give --vmstat and/or --iostat")
    try:
        vm = parse_vmstat(args.vmstat.read_text(encoding="utf-8")) if args.vmstat else []
        io = parse_iostat(args.iostat.read_text(encoding="utf-8")) if args.iostat else {}
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 2
    rows = use_table(vm, io, args.cpus)
    print(f"{'resource':12} {'check':30} {'value':>12}  verdict")
    for res, check, value, v in rows:
        print(f"{res:12} {check:30} {value:>12}  {v}")
    return 1 if any(r[3] == "CRIT" for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
