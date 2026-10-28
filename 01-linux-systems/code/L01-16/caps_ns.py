#!/usr/bin/env python3
"""Capability decode, namespace তুলনা ও cgroup path — container-এর ভিত্তি পর্যবেক্ষণ (read-only)।

Commands:
  python3 caps_ns.py caps 00000000a80425fb             # hex bitmask → capability নাম (capsh --decode-এর মতো)
  python3 caps_ns.py status /proc/<PID>/status         # CapInh/Prm/Eff/Bnd/Amb + ঝুঁকিপূর্ণ capability
  ls -l /proc/1/ns > host.txt; ls -l /proc/<PID>/ns > other.txt
  python3 caps_ns.py ns host.txt other.txt             # কোন namespace আলাদা
  python3 caps_ns.py cgroup /proc/<PID>/cgroup
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# include/uapi/linux/capability.h অনুযায়ী (Linux 5.9+ পর্যন্ত, 0–40)
CAPS = ["CHOWN", "DAC_OVERRIDE", "DAC_READ_SEARCH", "FOWNER", "FSETID", "KILL", "SETGID", "SETUID",
        "SETPCAP", "LINUX_IMMUTABLE", "NET_BIND_SERVICE", "NET_BROADCAST", "NET_ADMIN", "NET_RAW",
        "IPC_LOCK", "IPC_OWNER", "SYS_MODULE", "SYS_RAWIO", "SYS_CHROOT", "SYS_PTRACE", "SYS_PACCT",
        "SYS_ADMIN", "SYS_BOOT", "SYS_NICE", "SYS_RESOURCE", "SYS_TIME", "SYS_TTY_CONFIG", "MKNOD",
        "LEASE", "AUDIT_WRITE", "AUDIT_CONTROL", "SETFCAP", "MAC_OVERRIDE", "MAC_ADMIN", "SYSLOG",
        "WAKE_ALARM", "BLOCK_SUSPEND", "AUDIT_READ", "PERFMON", "BPF", "CHECKPOINT_RESTORE"]
DANGEROUS = {
    "SYS_ADMIN": "প্রায় root — mount, namespace, অনেক কিছু (\"the new root\")",
    "SYS_MODULE": "kernel module load — kernel নিয়ন্ত্রণ",
    "SYS_PTRACE": "অন্য process-এর memory পড়া/লেখা",
    "SYS_RAWIO": "সরাসরি device I/O",
    "DAC_READ_SEARCH": "যেকোনো file পড়া (permission উপেক্ষা)",
    "NET_ADMIN": "network configuration বদলানো",
    "BPF": "kernel-এ BPF program",
}
SET_NAMES = {"CapInh": "inheritable", "CapPrm": "permitted", "CapEff": "effective",
             "CapBnd": "bounding", "CapAmb": "ambient"}


def decode(mask_hex: str) -> list[str]:
    mask = int(mask_hex, 16)
    names = [f"CAP_{name}" for bit, name in enumerate(CAPS) if mask >> bit & 1]
    unknown = mask >> len(CAPS)
    if unknown:
        names.append(f"(unknown bits above {len(CAPS) - 1}: {unknown:#x})")
    return names


def parse_status(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        key, _, value = line.partition(":")
        if key in SET_NAMES or key in ("Name", "Uid", "NoNewPrivs", "Seccomp"):
            out[key] = value.strip()
    return out


NS_RE = re.compile(r"(\w+) -> '?(\w+):\[(\d+)\]'?")


def parse_ns(text: str) -> dict[str, int]:
    """`ls -l /proc/PID/ns`: 'net -> net:[4026531840]' → {'net': 4026531840}."""
    return {m.group(1): int(m.group(3)) for m in NS_RE.finditer(text)}


def compare_ns(a: dict[str, int], b: dict[str, int]) -> list[tuple[str, bool]]:
    return [(ns, a[ns] == b[ns]) for ns in sorted(set(a) & set(b))]


def parse_cgroup(text: str) -> str:
    """cgroup v2: একটি লাইন '0::/system.slice/x.service' → path।"""
    for line in text.splitlines():
        hid, _, rest = line.partition(":")
        controllers, _, path = rest.partition(":")
        if hid == "0" and controllers == "":
            return path
    raise ValueError("no cgroup v2 entry (0::) found — cgroup v1 system?")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Capabilities, namespaces and cgroup inspection.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("caps").add_argument("mask")
    sub.add_parser("status").add_argument("file", type=Path)
    n = sub.add_parser("ns")
    n.add_argument("a", type=Path)
    n.add_argument("b", type=Path)
    sub.add_parser("cgroup").add_argument("file", type=Path)
    args = p.parse_args(argv)

    try:
        if args.cmd == "caps":
            names = decode(args.mask)
            print(f"{len(names)} capability(ies): " + (", ".join(names) or "(none)"))
        elif args.cmd == "status":
            st = parse_status(args.file.read_text(encoding="utf-8"))
            print(f"process {st.get('Name', '?')}  Uid {st.get('Uid', '?')}  "
                  f"NoNewPrivs {st.get('NoNewPrivs', '?')}  Seccomp {st.get('Seccomp', '?')}")
            for key, label in SET_NAMES.items():
                if key in st:
                    names = decode(st[key])
                    print(f"  {label:11} {st[key]}  ({len(names)})")
            eff = {n.removeprefix("CAP_") for n in decode(st.get("CapEff", "0"))}
            risky = [c for c in DANGEROUS if c in eff]
            for c in risky:
                print(f"  RISK CAP_{c}: {DANGEROUS[c]}")
            return 1 if risky else 0
        elif args.cmd == "ns":
            rows = compare_ns(parse_ns(args.a.read_text(encoding="utf-8")),
                              parse_ns(args.b.read_text(encoding="utf-8")))
            for ns, same in rows:
                print(f"  {ns:18} {'shared' if same else 'ISOLATED'}")
        else:
            print(parse_cgroup(args.file.read_text(encoding="utf-8")))
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
