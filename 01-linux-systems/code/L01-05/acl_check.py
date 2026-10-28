#!/usr/bin/env python3
"""POSIX ACL decision — `getfacl` output থেকে নির্দিষ্ট user-এর access ও effective permission।

POSIX ACL algorithm (সরলীকৃত, acl(5) অনুযায়ী):
  1. uid == file owner        → user:: entry (mask প্রযোজ্য নয়)
  2. named user:NAME: মেলে    → সেই entry AND mask
  3. user-এর কোনো group মেলে (owning group group:: বা named group:NAME:)
                               → মেলা entry-গুলোর কোনোটিতে (AND mask) অধিকার থাকলে allowed;
                                 group মিললে কিন্তু কোনোটিতে অধিকার না থাকলে denied
  4. অন্যথায়                 → other:: entry

Usage:
  getfacl -p /srv/project/report.txt > acl.txt
  python3 acl_check.py acl.txt --user alice --groups alice,developers --op w
  python3 acl_check.py acl.txt --effective
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

BITS = {"r": 4, "w": 2, "x": 1}


def perm_bits(text: str) -> int:
    """'rw-' → 6."""
    if len(text) != 3 or any(c not in "rwx-" for c in text):
        raise ValueError(f"invalid permission {text!r}")
    return sum(BITS[c] for c in text if c != "-")


def bits_text(bits: int) -> str:
    return "".join(c if bits & BITS[c] else "-" for c in "rwx")


@dataclass
class Acl:
    owner: str = ""
    group: str = ""
    user_obj: int = 0
    group_obj: int = 0
    other: int = 0
    mask: int | None = None  # শুধু named entry থাকলে থাকে
    users: dict[str, int] = field(default_factory=dict)
    groups: dict[str, int] = field(default_factory=dict)

    def masked(self, bits: int) -> int:
        return bits if self.mask is None else bits & self.mask


def parse_getfacl(text: str) -> Acl:
    acl = Acl()
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip() if not raw.startswith("# owner") and not raw.startswith("# group") else raw
        if raw.startswith("# owner:"):
            acl.owner = raw.split(":", 1)[1].strip()
            continue
        if raw.startswith("# group:"):
            acl.group = raw.split(":", 1)[1].strip()
            continue
        if not line or line.startswith("default:"):
            continue  # default ACL নতুন file-এর জন্য; এই file-এর access-এ প্রভাব নেই
        kind, name, perms = line.split(":")
        bits = perm_bits(perms.strip())
        if kind == "user":
            if name:
                acl.users[name] = bits
            else:
                acl.user_obj = bits
        elif kind == "group":
            if name:
                acl.groups[name] = bits
            else:
                acl.group_obj = bits
        elif kind == "mask":
            acl.mask = bits
        elif kind == "other":
            acl.other = bits
        else:
            raise ValueError(f"unknown ACL entry {raw!r}")
    if not acl.owner:
        raise ValueError("missing '# owner:' header — use getfacl without --omit-header")
    return acl


def decide(acl: Acl, user: str, groups: set[str], op: str) -> tuple[bool, str]:
    need = BITS[op]
    if user == acl.owner:
        return bool(acl.user_obj & need), f"owner entry user::{bits_text(acl.user_obj)}"
    if user in acl.users:
        eff = acl.masked(acl.users[user])
        return bool(eff & need), f"named user entry user:{user}:{bits_text(acl.users[user])} (effective {bits_text(eff)})"
    matched = []
    if acl.group in groups:
        matched.append((f"group::{bits_text(acl.group_obj)}", acl.masked(acl.group_obj)))
    for g in sorted(groups & set(acl.groups)):
        matched.append((f"group:{g}:{bits_text(acl.groups[g])}", acl.masked(acl.groups[g])))
    if matched:
        ok = any(eff & need for _, eff in matched)
        return ok, "group entries " + ", ".join(f"{n} (effective {bits_text(e)})" for n, e in matched)
    return bool(acl.other & need), f"other entry other::{bits_text(acl.other)}"


def effective_table(acl: Acl) -> list[str]:
    rows = [f"user::{bits_text(acl.user_obj)}   (owner {acl.owner})"]
    rows += [f"user:{n}:{bits_text(b)}   effective {bits_text(acl.masked(b))}" for n, b in sorted(acl.users.items())]
    rows.append(f"group::{bits_text(acl.group_obj)}   effective {bits_text(acl.masked(acl.group_obj))}  (group {acl.group})")
    rows += [f"group:{n}:{bits_text(b)}   effective {bits_text(acl.masked(b))}" for n, b in sorted(acl.groups.items())]
    rows.append(f"mask::{bits_text(acl.mask) if acl.mask is not None else '(none)'}")
    rows.append(f"other::{bits_text(acl.other)}")
    return rows


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Evaluate POSIX ACLs from getfacl output.")
    p.add_argument("getfacl_file", type=Path)
    p.add_argument("--effective", action="store_true", help="সব entry-র effective permission")
    p.add_argument("--user")
    p.add_argument("--groups", default="", help="comma-separated group names of the user")
    p.add_argument("--op", choices=("r", "w", "x"))
    args = p.parse_args(argv)
    try:
        acl = parse_getfacl(args.getfacl_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.effective or not args.user:
        for row in effective_table(acl):
            print(row)
        return 0
    if not args.op:
        p.error("--op is required with --user")
    ok, why = decide(acl, args.user, {g for g in args.groups.split(",") if g}, args.op)
    print(f"{'ALLOWED' if ok else 'DENIED'}  {why}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
