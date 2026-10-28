#!/usr/bin/env python3
"""Installed package inventory — সবচেয়ে বড় package ও দুই server-এর package drift।

Inventory তৈরি (read-only command):
  Ubuntu: dpkg-query -W -f='${Package}\\t${Version}\\t${Installed-Size}\\n' > server-a.tsv
          (Installed-Size = KiB)
  Fedora: rpm -qa --queryformat '%{NAME}\\t%{VERSION}-%{RELEASE}\\t%{SIZE}\\n' > server-f.tsv
          (SIZE = byte)

Usage:
  python3 pkg_inventory.py top server-a.tsv --n 5
  python3 pkg_inventory.py diff server-a.tsv server-b.tsv
  python3 pkg_inventory.py top server-f.tsv --format rpm
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    size_kib: int


def parse_inventory(text: str, fmt: str = "dpkg") -> dict[str, Package]:
    """TSV → {name: Package}. dpkg size KiB-এ, rpm size byte-এ (KiB-এ রূপান্তর)।"""
    if fmt not in ("dpkg", "rpm"):
        raise ValueError(f"unknown format {fmt!r}")
    packages: dict[str, Package] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise ValueError(f"line {lineno}: expected 3 tab-separated fields, got {len(parts)}")
        name, version, size_raw = parts
        size = int(size_raw) if size_raw.strip() else 0  # কিছু meta-package-এর size খালি
        size_kib = size if fmt == "dpkg" else round(size / 1024)
        # একই নামের একাধিক architecture (যেমন libc6:amd64, libc6:i386) — নামেই ধরা থাকে
        packages[name] = Package(name, version, size_kib)
    return packages


def top_packages(pkgs: dict[str, Package], n: int) -> list[Package]:
    return sorted(pkgs.values(), key=lambda p: (-p.size_kib, p.name))[:n]


def diff_inventories(a: dict[str, Package], b: dict[str, Package]):
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    changed = sorted((n, a[n].version, b[n].version) for n in set(a) & set(b) if a[n].version != b[n].version)
    return only_a, only_b, changed


def human_kib(kib: int) -> str:
    return f"{kib / 1024:.1f} MiB" if kib >= 1024 else f"{kib} KiB"


def load(path: Path, fmt: str) -> dict[str, Package]:
    return parse_inventory(path.read_text(encoding="utf-8"), fmt)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Analyse dpkg/rpm package inventories.")
    p.add_argument("--format", choices=("dpkg", "rpm"), default="dpkg")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("top")
    t.add_argument("inventory", type=Path)
    t.add_argument("--n", type=int, default=10)
    d = sub.add_parser("diff")
    d.add_argument("a", type=Path)
    d.add_argument("b", type=Path)
    args = p.parse_args(argv)

    try:
        if args.cmd == "top":
            pkgs = load(args.inventory, args.format)
            total = sum(x.size_kib for x in pkgs.values())
            print(f"{len(pkgs)} packages, total {human_kib(total)}")
            for x in top_packages(pkgs, args.n):
                print(f"  {human_kib(x.size_kib):>10}  {x.name}  {x.version}")
        else:
            a, b = load(args.a, args.format), load(args.b, args.format)
            only_a, only_b, changed = diff_inventories(a, b)
            print(f"only in {args.a.name}: {len(only_a)}")
            for n in only_a:
                print(f"  - {n} {a[n].version}")
            print(f"only in {args.b.name}: {len(only_b)}")
            for n in only_b:
                print(f"  + {n} {b[n].version}")
            print(f"version differs: {len(changed)}")
            for n, va, vb in changed:
                print(f"  ~ {n}: {va} -> {vb}")
            return 1 if (only_a or only_b or changed) else 0  # drift থাকলে 1
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
