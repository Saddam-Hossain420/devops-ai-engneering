#!/usr/bin/env python3
"""MTU, MSS, tunnel overhead, IPv4 fragmentation, path MTU discovery ও DHCP lease timer হিসাব।

Commands:
  python3 mtu_calc.py mss --mtu 1500                     # TCP MSS (IPv4 ও IPv6)
  python3 mtu_calc.py ping-size --mtu 1500               # DF সহ সবচেয়ে বড় ping payload
  python3 mtu_calc.py tunnel --mtu 1500 vxlan wireguard4 # tunnel-এর ভেতরের MTU
  python3 mtu_calc.py fragment --size 3000 --mtu 1500    # ICMP payload কীভাবে fragment হয়
  python3 mtu_calc.py pmtud --path 1500,1500,1400,1500   # binary search দিয়ে path MTU (simulation)
  python3 mtu_calc.py lease 86400                        # DHCP T1/T2

শুধু হিসাব — কোনো packet পাঠায় না।
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

IP_HEADER = {"ipv4": 20, "ipv6": 40}
TCP_HEADER = 20
UDP_HEADER = 8
ICMP_HEADER = 8
TCP_TIMESTAMPS = 12  # Linux-এ default চালু; প্রতিটি segment-এ ১২ byte option

# Encapsulation overhead: ভেতরের IP packet-এর বাইরে যা যোগ হয় (underlay MTU থেকে বাদ যায়)
TUNNELS = {
    "vxlan": 14 + 20 + 8 + 8,       # inner Ethernet + outer IPv4 + UDP + VXLAN = 50
    "vxlan6": 14 + 40 + 8 + 8,      # IPv6 underlay = 70
    "wireguard4": 20 + 8 + 32,      # outer IPv4 + UDP + WireGuard header/auth tag = 60
    "wireguard6": 40 + 8 + 32,      # = 80 → তাই WireGuard default MTU 1420
    "gre": 20 + 4,                  # outer IPv4 + GRE base header = 24
    "ipip": 20,
    "pppoe": 8,
    "vlan": 4,                      # 802.1Q tag (L02-02) — Ethernet frame-এ, সাধারণত IP MTU কমায় না
}


def mss(mtu: int, ip: str = "ipv4", tcp_options: int = 0) -> int:
    """TCP segment-এ সর্বোচ্চ data: MTU − IP − TCP header − option।"""
    return mtu - IP_HEADER[ip] - TCP_HEADER - tcp_options


def max_ping_payload(mtu: int, ip: str = "ipv4") -> int:
    """`ping -M do -s N`-এর সর্বোচ্চ N: MTU − IP − ICMP header (1500 → 1472)।"""
    return mtu - IP_HEADER[ip] - ICMP_HEADER


def inner_mtu(outer_mtu: int, stack: list[str]) -> int:
    """Tunnel-এর পর tunnel (যেমন VXLAN-এর ভেতরে WireGuard) — প্রতিটির overhead বাদ।"""
    unknown = [t for t in stack if t not in TUNNELS]
    if unknown:
        raise ValueError(f"unknown tunnel type(s): {', '.join(unknown)} (known: {', '.join(TUNNELS)})")
    return outer_mtu - sum(TUNNELS[t] for t in stack)


def fragments(l4_len: int, mtu: int) -> list[tuple[int, int, bool]]:
    """IPv4 fragmentation: (offset byte-এ, data length, more-fragments flag)।
    শেষটি ছাড়া প্রতিটি fragment-এর data ৮-এর গুণিতক (offset ৮-byte এককে রাখা হয়)।"""
    per = (mtu - IP_HEADER["ipv4"]) // 8 * 8
    if per <= 0:
        raise ValueError("MTU too small")
    out, off = [], 0
    while off < l4_len:
        n = min(per, l4_len - off)
        out.append((off, n, off + n < l4_len))
        off += n
    return out


def path_mtu(hops: list[int]) -> int:
    return min(hops)


def pmtud_search(probe: Callable[[int], bool], lo: int = 576, hi: int = 9000) -> tuple[int, int]:
    """DF set করা probe দিয়ে binary search (tracepath/PLPMTUD-এর মূল ধারণা)। (MTU, probe সংখ্যা)।
    probe(size) = size byte-এর packet পৌঁছাল কিনা।"""
    if not probe(lo):
        raise ValueError(f"even {lo} bytes fails — path broken or ICMP blocked entirely")
    probes = 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        probes += 1
        if probe(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo, probes


def lease_timers(lease: int) -> tuple[int, int]:
    """DHCP (RFC 2131): T1 = 50% → মূল server-এ renew; T2 = 87.5% → যেকোনো server-এ rebind।"""
    return lease // 2, lease * 7 // 8


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="MTU / MSS / fragmentation calculator.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("mss", "ping-size"):
        s = sub.add_parser(name)
        s.add_argument("--mtu", type=int, default=1500)
    t = sub.add_parser("tunnel")
    t.add_argument("--mtu", type=int, default=1500)
    t.add_argument("stack", nargs="+")
    f = sub.add_parser("fragment")
    f.add_argument("--size", type=int, required=True, help="ICMP payload (ping -s)")
    f.add_argument("--mtu", type=int, default=1500)
    pm = sub.add_parser("pmtud")
    pm.add_argument("--path", required=True, help="comma-separated hop MTUs, e.g. 1500,1400,1500")
    le = sub.add_parser("lease")
    le.add_argument("seconds", type=int)
    args = ap.parse_args(argv)

    try:
        if args.cmd == "mss":
            for ip in ("ipv4", "ipv6"):
                print(f"{ip}: MSS {mss(args.mtu, ip)}  (with TCP timestamps: {mss(args.mtu, ip, TCP_TIMESTAMPS)} data/segment)")
        elif args.cmd == "ping-size":
            print(f"Linux:   ping -M do -s {max_ping_payload(args.mtu)} HOST")
            print(f"IPv6:    ping -6 -M do -s {max_ping_payload(args.mtu, 'ipv6')} HOST")
            print(f"Windows: ping -f -l {max_ping_payload(args.mtu)} HOST")
        elif args.cmd == "tunnel":
            m = args.mtu
            for layer in args.stack:
                nm = inner_mtu(m, [layer])
                print(f"{m:>5} - {layer:<10} ({TUNNELS[layer]:>2} bytes) = {nm}")
                m = nm
            print(f"inner MTU {m}  → TCP MSS {mss(m)}  → max ping -s {max_ping_payload(m)}")
        elif args.cmd == "fragment":
            frs = fragments(args.size + ICMP_HEADER, args.mtu)
            print(f"ICMP payload {args.size} + header {ICMP_HEADER} = {args.size + ICMP_HEADER} bytes over MTU {args.mtu}:")
            for off, n, more in frs:
                print(f"  offset {off:>5} (field {off // 8:>4})  data {n:>5}  packet {n + 20:>5}  MF={int(more)}")
            print(f"{len(frs)} fragment(s); losing any one loses the whole packet")
        elif args.cmd == "pmtud":
            hops = [int(x) for x in args.path.split(",")]
            found, probes = pmtud_search(lambda size: size <= path_mtu(hops))
            print(f"hops {hops} → path MTU {found} (found with {probes} DF probes; true {path_mtu(hops)})")
        elif args.cmd == "lease":
            t1, t2 = lease_timers(args.seconds)
            print(f"lease {args.seconds}s: T1 renew at {t1}s, T2 rebind at {t2}s, expire at {args.seconds}s")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
