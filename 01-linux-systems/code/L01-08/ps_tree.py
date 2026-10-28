#!/usr/bin/env python3
"""Process tree ও state বিশ্লেষণ — `ps` output থেকে।

Input তৈরি (read-only):
  ps -eo pid,ppid,stat,user,comm --no-headers > ps.txt

Usage:
  python3 ps_tree.py ps.txt                 # tree + state সারাংশ + zombie/D-state সতর্কতা
  python3 ps_tree.py ps.txt --root 1234     # একটি process-এর subtree
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

STATE_MEANING = {
    "R": "running / runnable (CPU-তে বা queue-তে)",
    "S": "interruptible sleep (কিছুর অপেক্ষায় — সবচেয়ে সাধারণ)",
    "D": "uninterruptible sleep (সাধারণত disk/NFS I/O; signal-এও জাগে না)",
    "T": "stopped (Ctrl+Z বা SIGSTOP)",
    "t": "stopped by debugger",
    "Z": "zombie (শেষ হয়েছে, parent এখনো exit status নেয়নি)",
    "I": "idle kernel thread",
    "X": "dead",
}


@dataclass(frozen=True)
class Proc:
    pid: int
    ppid: int
    stat: str
    user: str
    comm: str

    @property
    def state(self) -> str:
        return self.stat[0]


def parse_ps(text: str) -> dict[int, Proc]:
    procs: dict[int, Proc] = {}
    for line in text.splitlines():
        parts = line.split(None, 4)  # comm-এ space থাকতে পারে, তাই সর্বোচ্চ ৫ ভাগ
        if len(parts) < 5 or not parts[0].isdigit():
            continue  # header বা ভাঙা লাইন
        pid, ppid, stat, user, comm = parts
        procs[int(pid)] = Proc(int(pid), int(ppid), stat, user, comm.strip())
    return procs


def children_map(procs: dict[int, Proc]) -> dict[int, list[int]]:
    kids: dict[int, list[int]] = defaultdict(list)
    for p in procs.values():
        kids[p.ppid].append(p.pid)
    for v in kids.values():
        v.sort()
    return kids


def render_tree(procs: dict[int, Proc], root: int) -> list[str]:
    kids = children_map(procs)
    lines: list[str] = []

    def walk(pid: int, prefix: str, last: bool, depth: int) -> None:
        p = procs[pid]
        branch = "" if depth == 0 else ("└─ " if last else "├─ ")
        lines.append(f"{prefix}{branch}{p.comm} ({p.pid}) [{p.stat}] {p.user}")
        child_prefix = prefix + ("" if depth == 0 else ("   " if last else "│  "))
        children = [c for c in kids.get(pid, []) if c in procs]
        for i, c in enumerate(children):
            walk(c, child_prefix, i == len(children) - 1, depth + 1)

    walk(root, "", True, 0)
    return lines


def warnings(procs: dict[int, Proc]) -> list[str]:
    out = []
    zombies_by_parent = Counter(p.ppid for p in procs.values() if p.state == "Z")
    for ppid, n in zombies_by_parent.items():
        parent = procs.get(ppid)
        name = f"{parent.comm} ({ppid})" if parent else str(ppid)
        out.append(f"ZOMBIE: {n} zombie child(ren) of {name} — parent does not wait(); fix/restart the parent")
    for p in procs.values():
        if p.state == "D":
            out.append(f"D-STATE: {p.comm} ({p.pid}) is in uninterruptible I/O wait — check disk/NFS")
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Analyse process tree and states from ps output.")
    p.add_argument("ps_file", type=Path)
    p.add_argument("--root", type=int, default=1)
    args = p.parse_args(argv)
    try:
        procs = parse_ps(args.ps_file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: file not found: {args.ps_file}", file=sys.stderr)
        return 2
    if args.root not in procs:
        print(f"error: PID {args.root} not in input", file=sys.stderr)
        return 2
    for line in render_tree(procs, args.root):
        print(line)
    print("\nstates:")
    for state, n in sorted(Counter(pr.state for pr in procs.values()).items()):
        print(f"  {state}  {n:>3}  {STATE_MEANING.get(state, '?')}")
    warns = warnings(procs)
    for w in warns:
        print(w)
    return 1 if warns else 0


if __name__ == "__main__":
    raise SystemExit(main())
