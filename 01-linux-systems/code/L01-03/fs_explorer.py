#!/usr/bin/env python3
"""Filesystem explorer — FHS directory-র অর্থ, mount table ও inode/link পরীক্ষা।

Commands:
  python3 fs_explorer.py fhs /var/log/nginx/access.log   # path-টি FHS-এর কোন অংশে, কেন
  python3 fs_explorer.py mounts /proc/mounts             # mount table সারাংশ (Linux)
  python3 fs_explorer.py links                           # temporary dir-এ hard/symbolic link experiment
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

# Filesystem Hierarchy Standard — দীর্ঘ prefix আগে মেলানো হয়
FHS = {
    "/": "root — পুরো tree-এর শুরু",
    "/bin": "অপরিহার্য user command (আধুনিক Ubuntu/Fedora-তে /usr/bin-এর symlink)",
    "/boot": "kernel ও bootloader file",
    "/dev": "device file (devtmpfs — kernel তৈরি করে)",
    "/etc": "system-wide configuration (text file, মানুষ সম্পাদনা করে)",
    "/home": "সাধারণ user-দের home directory",
    "/opt": "third-party, স্বয়ংসম্পূর্ণ software",
    "/proc": "process ও kernel তথ্য (virtual, disk-এ নেই)",
    "/root": "root user-এর home",
    "/run": "চলমান অবস্থার data (PID file, socket); reboot-এ মুছে যায় (tmpfs)",
    "/srv": "এই system যে service দেয় তার data (যেমন web content)",
    "/sys": "kernel-এর device ও driver তথ্য (sysfs, virtual)",
    "/tmp": "অস্থায়ী file; reboot-এ বা নিয়মিত পরিষ্কার হতে পারে",
    "/usr": "installed software (read-only মনোভাব; package manager-এর এলাকা)",
    "/usr/bin": "user command",
    "/usr/lib": "library ও internal file",
    "/usr/local": "হাতে install করা software (package manager-এর বাইরে)",
    "/usr/share": "architecture-নিরপেক্ষ data (doc, man page)",
    "/var": "পরিবর্তনশীল data — বড় হয়",
    "/var/cache": "পুনরায় তৈরিযোগ্য cache (মুছলে ক্ষতি নেই, আবার তৈরি হবে)",
    "/var/lib": "service-এর স্থায়ী state (database, package database) — backup করুন",
    "/var/log": "log file — disk পূর্ণ হওয়ার সাধারণ কারণ",
    "/var/tmp": "reboot-এর পরেও থাকা অস্থায়ী file",
}
PSEUDO_FS = {"proc", "sysfs", "devtmpfs", "devpts", "tmpfs", "cgroup", "cgroup2", "securityfs",
             "debugfs", "tracefs", "mqueue", "hugetlbfs", "pstore", "bpf", "configfs", "fusectl",
             "autofs", "efivarfs", "binfmt_misc", "nsfs", "overlay", "squashfs"}


def fhs_lookup(path: str) -> tuple[str, str]:
    """সবচেয়ে দীর্ঘ মেলা FHS prefix ও তার অর্থ।"""
    p = PurePosixPath(path)
    if not p.is_absolute():
        raise ValueError("path must be absolute (start with /)")
    for candidate in [p, *p.parents]:
        key = str(candidate)
        if key in FHS:
            return key, FHS[key]
    return "/", FHS["/"]


@dataclass(frozen=True)
class Mount:
    device: str
    mountpoint: str
    fstype: str
    options: tuple[str, ...]

    @property
    def read_only(self) -> bool:
        return "ro" in self.options


def unescape(field: str) -> str:
    """/proc/mounts space-কে \\040, tab-কে \\011 লেখে।"""
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def parse_mounts(text: str) -> list[Mount]:
    mounts = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        mounts.append(Mount(unescape(parts[0]), unescape(parts[1]), parts[2], tuple(parts[3].split(","))))
    return mounts


def links_experiment(directory: Path) -> list[str]:
    """Original file, hard link ও symlink তৈরি করে original মুছে ফলাফল দেখায়।"""
    out: list[str] = []
    original = directory / "original.txt"
    hard = directory / "hard.txt"
    soft = directory / "soft.txt"
    original.write_text("data\n", encoding="utf-8")
    os.link(original, hard)
    try:
        os.symlink(original.name, soft)  # relative target — directory সরালেও কাজ করে
        have_symlink = True
    except (OSError, NotImplementedError):  # Windows-এ বিশেষ অধিকার ছাড়া symlink নাও হতে পারে
        have_symlink = False
        out.append("symlink: not permitted on this system (skipped)")

    st = original.stat()
    out.append(f"original inode={st.st_ino} links={st.st_nlink}")
    out.append(f"hard     inode={hard.stat().st_ino} same_inode={hard.stat().st_ino == st.st_ino}")
    if have_symlink:
        out.append(f"soft     own_inode={soft.lstat().st_ino != st.st_ino} -> {os.readlink(soft)}")

    original.unlink()
    out.append("original deleted")
    out.append(f"hard still readable={hard.read_text(encoding='utf-8') == 'data' + chr(10)} links={hard.stat().st_nlink}")
    if have_symlink:
        out.append(f"soft dangling={soft.is_symlink() and not soft.exists()}")
    return out


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Filesystem hierarchy, mounts and links explorer.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fhs").add_argument("path")
    sub.add_parser("mounts").add_argument("file", nargs="?", default="/proc/mounts")
    sub.add_parser("links")
    args = p.parse_args(argv)

    try:
        if args.cmd == "fhs":
            prefix, meaning = fhs_lookup(args.path)
            print(f"{args.path}\n  belongs to {prefix}: {meaning}")
        elif args.cmd == "mounts":
            mounts = parse_mounts(Path(args.file).read_text(encoding="utf-8"))
            real = [m for m in mounts if m.fstype not in PSEUDO_FS]
            print(f"{len(mounts)} mounts, {len(real)} on real/block filesystems:")
            for m in real:
                print(f"  {m.mountpoint:20} {m.fstype:6} {'ro' if m.read_only else 'rw'}  {m.device}")
            pseudo = sorted({m.fstype for m in mounts if m.fstype in PSEUDO_FS})
            print(f"special (virtual / loop / overlay) types: {', '.join(pseudo)}")
        else:
            with tempfile.TemporaryDirectory(prefix="links-") as d:
                for line in links_experiment(Path(d)):
                    print(line)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
