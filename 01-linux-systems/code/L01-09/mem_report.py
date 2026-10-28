#!/usr/bin/env python3
"""Memory, load ও OOM বিশ্লেষণ — /proc file ও kernel log থেকে (read-only)।

Commands:
  python3 mem_report.py meminfo [/proc/meminfo]
  python3 mem_report.py load [/proc/loadavg] --cpus 4
  python3 mem_report.py pressure [/proc/pressure/memory]
  python3 mem_report.py oom kernel.log           # journalctl -k > kernel.log
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def parse_meminfo(text: str) -> dict[str, int]:
    """'MemTotal:  16314064 kB' → {'MemTotal': 16314064} (kB)."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+(?:\(\w+\))?):\s+(\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def memory_summary(mi: dict[str, int]) -> dict[str, float]:
    total = mi["MemTotal"]
    available = mi.get("MemAvailable", mi.get("MemFree", 0))
    cache = mi.get("Cached", 0) + mi.get("Buffers", 0) + mi.get("SReclaimable", 0)
    swap_total = mi.get("SwapTotal", 0)
    swap_used = swap_total - mi.get("SwapFree", 0)
    return {
        "total_gib": round(total / 1024**2, 2),
        "free_gib": round(mi.get("MemFree", 0) / 1024**2, 2),
        "available_gib": round(available / 1024**2, 2),
        "cache_gib": round(cache / 1024**2, 2),
        "used_percent": round(100 * (total - available) / total, 1),
        "swap_used_percent": round(100 * swap_used / swap_total, 1) if swap_total else 0.0,
    }


def memory_verdict(s: dict[str, float]) -> str:
    if s["used_percent"] >= 90:
        return "CRITICAL: available memory < 10% — OOM ঝুঁকি"
    if s["used_percent"] >= 80:
        return "WARNING: available memory < 20%"
    if s["free_gib"] < 0.1 * s["total_gib"] and s["cache_gib"] > 0:
        return "OK: 'free' কম দেখালেও অধিকাংশ page cache — দরকার হলে kernel ফেরত নেয়"
    return "OK"


def parse_loadavg(text: str) -> tuple[float, float, float, int, int]:
    """'2.10 1.50 0.90 3/512 12345' → (1m, 5m, 15m, running, total)."""
    parts = text.split()
    running, total = parts[3].split("/")
    return float(parts[0]), float(parts[1]), float(parts[2]), int(running), int(total)


def load_verdict(load1: float, load15: float, cpus: int) -> str:
    per_cpu = load1 / cpus
    trend = "বাড়ছে" if load1 > load15 * 1.2 else ("কমছে" if load1 < load15 * 0.8 else "স্থির")
    if per_cpu > 1.5:
        level = "OVERLOADED: runnable/D-state task CPU সংখ্যার চেয়ে অনেক বেশি"
    elif per_cpu > 1.0:
        level = "BUSY: কিছু task অপেক্ষায়"
    else:
        level = "OK"
    return f"{level} (load/cpu = {per_cpu:.2f}, trend {trend})"


def parse_pressure(text: str) -> dict[str, dict[str, float]]:
    """PSI: 'some avg10=1.23 avg60=0.50 avg300=0.10 total=12345'."""
    out: dict[str, dict[str, float]] = {}
    for line in text.splitlines():
        kind, *fields = line.split()
        out[kind] = {k: float(v) for k, v in (f.split("=") for f in fields)}
    return out


@dataclass(frozen=True)
class OomKill:
    pid: int
    comm: str
    anon_rss_mib: float
    cgroup_limit: bool


OOM_RE = re.compile(
    r"(?P<scope>Memory cgroup out of memory|Out of memory): Killed process (?P<pid>\d+) \((?P<comm>[^)]+)\)"
    r".*?anon-rss:(?P<anon>\d+)kB"
)


def parse_oom(text: str) -> list[OomKill]:
    kills = []
    for line in text.splitlines():
        m = OOM_RE.search(line)
        if m:
            kills.append(OomKill(int(m["pid"]), m["comm"], round(int(m["anon"]) / 1024, 1),
                                 m["scope"].startswith("Memory cgroup")))
    return kills


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Memory, load and OOM analysis.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("meminfo").add_argument("file", nargs="?", default="/proc/meminfo")
    lp = sub.add_parser("load")
    lp.add_argument("file", nargs="?", default="/proc/loadavg")
    lp.add_argument("--cpus", type=int, default=os.cpu_count() or 1)
    sub.add_parser("pressure").add_argument("file", nargs="?", default="/proc/pressure/memory")
    sub.add_parser("oom").add_argument("file")
    args = p.parse_args(argv)

    try:
        if args.cmd == "meminfo":
            s = memory_summary(parse_meminfo(read(args.file)))
            print(f"total {s['total_gib']} GiB | free {s['free_gib']} | available {s['available_gib']} | "
                  f"cache {s['cache_gib']} | used {s['used_percent']}% | swap used {s['swap_used_percent']}%")
            print(memory_verdict(s))
        elif args.cmd == "load":
            l1, l5, l15, run, total = parse_loadavg(read(args.file))
            print(f"load {l1} {l5} {l15} | cpus {args.cpus} | runnable now {run}/{total} tasks")
            print(load_verdict(l1, l15, args.cpus))
        elif args.cmd == "pressure":
            for kind, v in parse_pressure(read(args.file)).items():
                print(f"{kind:5} avg10={v['avg10']}% avg60={v['avg60']}% avg300={v['avg300']}%")
        else:
            kills = parse_oom(read(args.file))
            for k in kills:
                scope = "cgroup/container limit" if k.cgroup_limit else "whole system"
                print(f"OOM kill: {k.comm} (pid {k.pid}) anon-rss {k.anon_rss_mib} MiB — {scope}")
            print(f"{len(kills)} OOM kill(s)")
            return 1 if kills else 0
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename} (Linux /proc only?)", file=sys.stderr)
        return 2
    except (KeyError, ValueError, IndexError) as exc:
        print(f"error: unexpected format: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
