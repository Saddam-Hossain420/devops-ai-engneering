#!/usr/bin/env python3
"""inventory.py — CSV host inventory পড়ে যাচাই, filter ও group (dataclass, Enum, type hint-এর অনুশীলন)।

  python3 inventory.py hosts.csv                       # সব valid host ও সমস্যার তালিকা
  python3 inventory.py hosts.csv --env prod --role web # filter
  python3 inventory.py hosts.csv --group-by env --json # group করে JSON

ভুল row পুরো file বাতিল করে না — আলাদা "problems" তালিকায় যায় (line নম্বরসহ)।
Exit: 0 সব row valid, 1 কিছু row বাতিল, 2 file/argument error।
"""
from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from pathlib import Path


class Env(StrEnum):          # (str, Enum) হলে str() → 'Env.PROD' (Python 3.11+)
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Role(StrEnum):
    WEB = "web"
    DB = "db"
    CACHE = "cache"
    WORKER = "worker"


@dataclass(frozen=True)
class Host:
    name: str
    ip: str
    env: Env
    role: Role
    cpu: int
    mem_gb: int
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_prod(self) -> bool:
        return self.env is Env.PROD


@dataclass
class Problem:
    line: int
    message: str


def parse_row(row: dict[str, str]) -> Host:
    """একটি CSV row থেকে Host; ভুল হলে ValueError (বার্তায় কোন field)।"""
    name = (row.get("name") or "").strip()
    if not name:
        raise ValueError("name is empty")
    try:
        ip = str(ipaddress.ip_address((row.get("ip") or "").strip()))
    except ValueError:
        raise ValueError(f"invalid ip {row.get('ip')!r}") from None
    try:
        env, role = Env(row["env"].strip()), Role(row["role"].strip())
    except (KeyError, ValueError, AttributeError):
        raise ValueError(f"unknown env/role {row.get('env')!r}/{row.get('role')!r}") from None
    try:
        cpu, mem = int(row["cpu"]), int(row["mem_gb"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("cpu/mem_gb must be integers") from None
    if cpu <= 0 or mem <= 0:
        raise ValueError("cpu/mem_gb must be positive")
    tags = tuple(t for t in (row.get("tags") or "").split(";") if t)
    return Host(name, ip, env, role, cpu, mem, tags)


def _data_lines(lines: Iterable[str]) -> Iterator[tuple[int, str]]:
    for n, line in enumerate(lines, 1):
        if line.strip() and not line.lstrip().startswith("#"):
            yield n, line


def load(text: str) -> tuple[list[Host], list[Problem]]:
    numbered = list(_data_lines(text.splitlines(keepends=True)))
    if not numbered:
        return [], [Problem(0, "no data")]
    reader = csv.DictReader(line for _, line in numbered)
    hosts: list[Host] = []
    problems: list[Problem] = []
    seen: dict[str, int] = {}
    for row in reader:
        n = numbered[reader.line_num - 1][0]       # quoted field একাধিক লাইনে গেলে row-এর শেষ লাইন
        try:
            host = parse_row(row)
        except ValueError as exc:
            problems.append(Problem(n, str(exc)))
            continue
        if host.name in seen:
            problems.append(Problem(n, f"duplicate name {host.name!r} (first on line {seen[host.name]})"))
            continue
        seen[host.name] = n
        hosts.append(host)
    return hosts, problems


def select(hosts: Iterable[Host], env: Env | None = None, role: Role | None = None) -> list[Host]:
    return [h for h in hosts if (env is None or h.env is env) and (role is None or h.role is role)]


def group_by(hosts: Iterable[Host], key: str) -> dict[str, list[Host]]:
    groups: dict[str, list[Host]] = defaultdict(list)
    for h in hosts:
        value = getattr(h, key)
        groups[value.value if isinstance(value, Enum) else str(value)].append(h)
    return dict(sorted(groups.items()))


def to_dict(h: Host) -> dict[str, object]:
    d = asdict(h)
    d["env"], d["role"], d["tags"] = h.env.value, h.role.value, list(h.tags)
    return d


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate, filter and group a CSV host inventory.")
    ap.add_argument("file", type=Path)
    ap.add_argument("--env", type=Env, choices=list(Env))
    ap.add_argument("--role", type=Role, choices=list(Role))
    ap.add_argument("--group-by", choices=["env", "role"])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        text = args.file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    hosts, problems = load(text)
    chosen = select(hosts, args.env, args.role)
    if args.json:
        body: object = ({k: [to_dict(h) for h in v] for k, v in group_by(chosen, args.group_by).items()}
                        if args.group_by else [to_dict(h) for h in chosen])
        print(json.dumps({"hosts": body, "problems": [asdict(p) for p in problems]}, indent=2))
    else:
        groups = group_by(chosen, args.group_by) if args.group_by else {"all": chosen}
        for key, items in groups.items():
            total_cpu = sum(h.cpu for h in items)
            print(f"[{key}] {len(items)} hosts, {total_cpu} cpu, {sum(h.mem_gb for h in items)} GB")
            for h in items:
                print(f"  {h.name:<12} {h.ip:<15} {h.env.value:<8} {h.role.value:<7} {','.join(h.tags)}")
        for p in problems:
            print(f"PROBLEM line {p.line}: {p.message}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
