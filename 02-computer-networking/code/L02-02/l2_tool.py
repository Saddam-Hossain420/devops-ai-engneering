#!/usr/bin/env python3
"""Layer 2 tool — MAC address বিশ্লেষণ, ARP/neighbor table audit, 802.1Q VLAN tag।

Commands:
  python3 l2_tool.py mac 52-54-00-AB-CD-EF
  ip neigh > neigh.txt && python3 l2_tool.py neigh neigh.txt
  python3 l2_tool.py vlan --vid 20 --pcp 5          # tag তৈরি
  python3 l2_tool.py vlan --decode 8100a014         # tag decode
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def normalize_mac(text: str) -> str:
    """'52-54-00-AB-CD-EF', '5254.00ab.cdef', '525400abcdef' → '52:54:00:ab:cd:ef'."""
    digits = re.sub(r"[^0-9a-fA-F]", "", text)
    if len(digits) != 12 or re.search(r"[^0-9a-fA-F:\-.]", text):
        raise ValueError(f"not a MAC address: {text!r}")
    return ":".join(digits[i:i + 2] for i in range(0, 12, 2)).lower()


def mac_info(mac: str) -> dict[str, object]:
    mac = normalize_mac(mac)
    first = int(mac[:2], 16)
    return {
        "mac": mac,
        "oui": mac[:8],
        "broadcast": mac == "ff:ff:ff:ff:ff:ff",
        "multicast": bool(first & 0x01),          # I/G bit: প্রথম octet-এর সবচেয়ে ছোট bit
        "locally_administered": bool(first & 0x02),  # U/L bit: VM, container, random MAC
    }


@dataclass(frozen=True)
class Neighbor:
    ip: str
    dev: str
    mac: str | None
    state: str


NEIGH_RE = re.compile(r"^(?P<ip>\S+) dev (?P<dev>\S+)(?: lladdr (?P<mac>\S+))?(?: router)?\s+(?P<state>[A-Z]+)")


def parse_neigh(text: str) -> list[Neighbor]:
    out = []
    for line in text.splitlines():
        m = NEIGH_RE.match(line.strip())
        if m:
            out.append(Neighbor(m["ip"], m["dev"], m["mac"].lower() if m["mac"] else None, m["state"]))
    return out


def audit_neigh(neigh: list[Neighbor]) -> list[str]:
    warnings = []
    by_mac: dict[str, list[str]] = defaultdict(list)
    for n in neigh:
        if n.mac:
            by_mac[n.mac].append(n.ip)
        if n.state in ("FAILED", "INCOMPLETE"):
            warnings.append(f"{n.ip} on {n.dev}: {n.state} — ARP-এর উত্তর নেই (host down, ভুল subnet বা VLAN?)")
    for mac, ips in by_mac.items():
        v4 = [ip for ip in ips if ":" not in ip]
        if len(v4) > 1:
            warnings.append(f"{mac} claims {len(v4)} IPv4 addresses {v4} — proxy/router হতে পারে, "
                            f"নয়তো ARP spoofing সন্দেহ করুন")
    return warnings


def vlan_tag(vid: int, pcp: int = 0, dei: int = 0) -> bytes:
    """802.1Q tag: TPID 0x8100 + TCI (PCP 3 bit | DEI 1 bit | VID 12 bit)."""
    if not 1 <= vid <= 4094:
        raise ValueError("VLAN ID must be 1-4094 (0 ও 4095 সংরক্ষিত)")
    if not 0 <= pcp <= 7 or dei not in (0, 1):
        raise ValueError("PCP 0-7, DEI 0/1")
    tci = (pcp << 13) | (dei << 12) | vid
    return bytes([0x81, 0x00, tci >> 8, tci & 0xFF])


def decode_vlan(tag: bytes) -> dict[str, int]:
    if len(tag) != 4 or tag[:2] != b"\x81\x00":
        raise ValueError("not an 802.1Q tag (TPID must be 0x8100)")
    tci = (tag[2] << 8) | tag[3]
    return {"pcp": tci >> 13, "dei": (tci >> 12) & 1, "vid": tci & 0x0FFF}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Layer 2 helper: MAC, ARP neighbors, VLAN tags.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("mac").add_argument("mac")
    sub.add_parser("neigh").add_argument("file", type=Path)
    v = sub.add_parser("vlan")
    v.add_argument("--vid", type=int)
    v.add_argument("--pcp", type=int, default=0)
    v.add_argument("--decode")
    args = p.parse_args(argv)

    try:
        if args.cmd == "mac":
            for k, val in mac_info(args.mac).items():
                print(f"{k:22} {val}")
        elif args.cmd == "neigh":
            neigh = parse_neigh(args.file.read_text(encoding="utf-8"))
            for n in neigh:
                print(f"  {n.ip:28} {n.dev:6} {n.mac or '-':17} {n.state}")
            warns = audit_neigh(neigh)
            for w in warns:
                print(f"WARN {w}")
            return 1 if warns else 0
        elif args.decode:
            d = decode_vlan(bytes.fromhex(args.decode))
            print(f"VLAN {d['vid']}  priority (PCP) {d['pcp']}  DEI {d['dei']}")
        else:
            if args.vid is None:
                p.error("give --vid or --decode")
            print(vlan_tag(args.vid, args.pcp).hex())
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
