#!/usr/bin/env python3
"""Linux permission tool — mode ব্যাখ্যা, umask হিসাব, access সিদ্ধান্ত, user তালিকা ও audit।

Commands:
  python3 perm_tool.py explain 640           # octal → symbolic + কে কী পারে
  python3 perm_tool.py explain rwsr-xr-x     # symbolic → octal
  python3 perm_tool.py umask 027             # নতুন file/directory-র default permission
  python3 perm_tool.py check --uid 1001 --gids 1001,33 --owner 0 --group 33 --mode 640 --op r
  python3 perm_tool.py users /etc/passwd     # login করতে পারে এমন user
  python3 perm_tool.py audit /srv            # world-writable ও setuid/setgid file (read-only)
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

CLASSES = ("owner", "group", "other")
BITS = {"r": 4, "w": 2, "x": 1}


def parse_mode(text: str) -> int:
    """'640', '0640', '4755' বা 'rwxr-x---' / 'rwsr-xr-x' → int mode (special bit সহ)."""
    text = text.strip()
    if text.isdigit():
        if any(c not in "01234567" for c in text) or len(text) > 4:
            raise ValueError(f"invalid octal mode {text!r}")
        return int(text, 8)
    if len(text) == 10:          # 'ls -l'-এর প্রথম অক্ষর (-, d, l) বাদ
        text = text[1:]
    if len(text) != 9:
        raise ValueError(f"symbolic mode must have 9 characters, got {text!r}")
    mode = 0
    for i, cls in enumerate(CLASSES):
        r, w, x = text[i * 3: i * 3 + 3]
        if r not in "r-" or w not in "w-":
            raise ValueError(f"invalid characters in {text!r}")
        mode |= (4 if r == "r" else 0) << (6 - i * 3)
        mode |= (2 if w == "w" else 0) << (6 - i * 3)
        special_lower, special_upper = {"owner": ("s", "S"), "group": ("s", "S"), "other": ("t", "T")}[cls]
        if x in ("x", special_lower):
            mode |= 1 << (6 - i * 3)
        elif x not in ("-", special_upper):
            raise ValueError(f"invalid execute character {x!r}")
        if x in (special_lower, special_upper):
            mode |= {"owner": 0o4000, "group": 0o2000, "other": 0o1000}[cls]
    return mode


def to_symbolic(mode: int) -> str:
    """int mode → 'rwsr-x---' (ls -l শৈলী, type অক্ষর ছাড়া)."""
    out = []
    specials = (0o4000, 0o2000, 0o1000)
    for i in range(3):
        bits = (mode >> (6 - i * 3)) & 7
        r = "r" if bits & 4 else "-"
        w = "w" if bits & 2 else "-"
        x = "x" if bits & 1 else "-"
        if mode & specials[i]:
            lower, upper = ("t", "T") if i == 2 else ("s", "S")
            x = lower if bits & 1 else upper  # বড় হাতের = special bit আছে কিন্তু execute নেই
        out.append(r + w + x)
    return "".join(out)


def describe(mode: int) -> list[str]:
    lines = []
    for i, cls in enumerate(CLASSES):
        bits = (mode >> (6 - i * 3)) & 7
        can = [name for name, flag in (("read", 4), ("write", 2), ("execute", 1)) if bits & flag]
        lines.append(f"{cls:5}: {', '.join(can) if can else 'nothing'}")
    if mode & 0o4000:
        lines.append("setuid: চালালে program file-এর owner-এর অধিকারে চলে")
    if mode & 0o2000:
        lines.append("setgid: file-এ group-এর অধিকারে চলে; directory-তে নতুন file directory-র group পায়")
    if mode & 0o1000:
        lines.append("sticky: directory-তে শুধু file-এর owner (বা root) file মুছতে/নাম বদলাতে পারে")
    return lines


def apply_umask(mask: int) -> tuple[int, int]:
    """নতুন file (base 666) ও directory (base 777)-এর permission।"""
    return 0o666 & ~mask, 0o777 & ~mask


def can_access(uid: int, gids: set[int], owner: int, group: int, mode: int, op: str) -> tuple[bool, str]:
    """Kernel-এর DAC নিয়ম (সরলীকৃত, ACL ও capability ছাড়া).

    প্রথম মেলা class-এর bit-ই সিদ্ধান্ত — owner মিললে group/other দেখা হয় না।
    root (uid 0) read/write সবসময় পারে; execute পারে যদি কোনো class-এ x থাকে।
    """
    flag = BITS[op]
    if uid == 0:
        if op != "x" or mode & 0o111:
            return True, "root bypasses permission checks"
        return False, "root: no execute bit set anywhere"
    if uid == owner:
        cls, bits = "owner", (mode >> 6) & 7
    elif group in gids:
        cls, bits = "group", (mode >> 3) & 7
    else:
        cls, bits = "other", mode & 7
    return bool(bits & flag), f"matched class: {cls} ({to_symbolic(mode)[CLASSES.index(cls) * 3:][:3]})"


@dataclass(frozen=True)
class User:
    name: str
    uid: int
    gid: int
    home: str
    shell: str


def parse_passwd(text: str) -> list[User]:
    """/etc/passwd: name:x:uid:gid:gecos:home:shell"""
    users = []
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) != 7:
            raise ValueError(f"invalid passwd line: {line!r}")
        users.append(User(parts[0], int(parts[2]), int(parts[3]), parts[5], parts[6]))
    return users


NOLOGIN = ("/usr/sbin/nologin", "/sbin/nologin", "/bin/false", "/usr/bin/false")


def login_users(users: list[User]) -> list[User]:
    return [u for u in users if u.shell not in NOLOGIN]


def audit(root: Path) -> list[str]:
    """Read-only: world-writable file ও setuid/setgid file। symlink অনুসরণ করে না।"""
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            try:
                st = p.lstat()
            except OSError:
                continue
            if stat.S_ISLNK(st.st_mode):
                continue
            mode = stat.S_IMODE(st.st_mode)
            kind = "dir " if stat.S_ISDIR(st.st_mode) else "file"
            if mode & 0o002 and not (stat.S_ISDIR(st.st_mode) and mode & 0o1000):
                findings.append(f"WORLD-WRITABLE {kind} {to_symbolic(mode)} {p}")
            if mode & 0o6000 and not stat.S_ISDIR(st.st_mode):
                findings.append(f"SETUID/SETGID  {kind} {to_symbolic(mode)} {p}")
    return findings


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Linux permission helper.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("explain").add_argument("mode")
    sub.add_parser("umask").add_argument("mask")
    c = sub.add_parser("check")
    for name in ("--uid", "--owner", "--group"):
        c.add_argument(name, type=int, required=True)
    c.add_argument("--gids", required=True, help="comma-separated group IDs of the user")
    c.add_argument("--mode", required=True)
    c.add_argument("--op", choices=("r", "w", "x"), required=True)
    sub.add_parser("users").add_argument("passwd_file", nargs="?", default="/etc/passwd")
    sub.add_parser("audit").add_argument("directory")
    args = p.parse_args(argv)

    try:
        if args.cmd == "explain":
            mode = parse_mode(args.mode)
            print(f"octal {mode:04o}   symbolic {to_symbolic(mode)}")
            for line in describe(mode):
                print("  " + line)
        elif args.cmd == "umask":
            mask = parse_mode(args.mask)
            f, d = apply_umask(mask)
            print(f"umask {mask:04o} → new file {f:04o} ({to_symbolic(f)}), new dir {d:04o} ({to_symbolic(d)})")
        elif args.cmd == "check":
            gids = {int(g) for g in args.gids.split(",") if g}
            ok, why = can_access(args.uid, gids, args.owner, args.group, parse_mode(args.mode), args.op)
            print(f"{'ALLOWED' if ok else 'DENIED'}  ({why})")
            return 0 if ok else 1
        elif args.cmd == "users":
            for u in login_users(parse_passwd(Path(args.passwd_file).read_text(encoding="utf-8"))):
                print(f"  {u.name:12} uid={u.uid:<6} home={u.home:20} shell={u.shell}")
        else:
            findings = audit(Path(args.directory))
            for f in findings:
                print(f)
            print(f"{len(findings)} finding(s)")
            return 1 if findings else 0
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
