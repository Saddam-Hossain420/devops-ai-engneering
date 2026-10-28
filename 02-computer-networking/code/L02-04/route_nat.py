#!/usr/bin/env python3
"""Routing ও NAT — kernel-এর route সিদ্ধান্ত ও SNAT/masquerade-এর translation table simulation।

Commands:
  ip route > routes.txt
  python3 route_nat.py lookup routes.txt 10.8.0.5          # কোন route, কোন next hop
  python3 route_nat.py nat --public 203.0.113.7 --ports 61000-61003 --flows flows.txt
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Route:
    dest: ipaddress.IPv4Network
    via: str | None
    dev: str | None
    metric: int
    kind: str  # unicast / blackhole / unreachable
    raw: str


def parse_routes(text: str) -> list[Route]:
    """`ip route` (IPv4) লাইন parse। 'default' = 0.0.0.0/0।"""
    routes = []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        kind = "unicast"
        if parts[0] in ("blackhole", "unreachable", "prohibit"):
            kind, parts = parts[0], parts[1:]
        dest = "0.0.0.0/0" if parts[0] == "default" else parts[0]
        net = ipaddress.ip_network(dest if "/" in dest else dest + "/32", strict=False)
        opts = dict(zip(parts[1::2], parts[2::2]))  # key value জোড়া (via X dev Y metric Z ...)
        routes.append(Route(net, opts.get("via"), opts.get("dev"), int(opts.get("metric", 0)), kind, line.strip()))
    return routes


def lookup(routes: list[Route], ip: str) -> Route | None:
    """Longest prefix match; সমান prefix-এ কম metric জেতে।"""
    addr = ipaddress.ip_address(ip)
    candidates = [r for r in routes if addr in r.dest]
    if not candidates:
        return None
    return min(candidates, key=lambda r: (-r.dest.prefixlen, r.metric))


class Nat:
    """SNAT/masquerade: (private ip, private port, dst) → public port; উল্টো পথে ফেরত মেলানো।"""

    def __init__(self, public_ip: str, port_range: range) -> None:
        self.public_ip = public_ip
        self.free = list(port_range)
        self.table: dict[tuple[str, int, str], int] = {}
        self.reverse: dict[tuple[int, str], tuple[str, int]] = {}

    def outbound(self, src_ip: str, src_port: int, dst: str) -> tuple[str, int]:
        key = (src_ip, src_port, dst)
        if key not in self.table:
            if not self.free:
                raise RuntimeError(f"NAT port exhaustion: no free port for {src_ip}:{src_port} → {dst}")
            port = self.free.pop(0)
            self.table[key] = port
            self.reverse[(port, dst)] = (src_ip, src_port)
        return self.public_ip, self.table[key]

    def inbound(self, public_port: int, from_dst: str) -> tuple[str, int] | None:
        """Reply এলে কোন private host-এ যাবে; table-এ না থাকলে drop (অযাচিত inbound)।"""
        return self.reverse.get((public_port, from_dst))


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # stderr-এও: error বার্তায় '→' আছে
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Routing lookup and NAT simulation.")
    sub = p.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("lookup")
    lk.add_argument("routes", type=Path)
    lk.add_argument("ips", nargs="+")
    nt = sub.add_parser("nat")
    nt.add_argument("--public", required=True)
    nt.add_argument("--ports", default="61000-61003")
    nt.add_argument("--flows", type=Path, required=True, help="লাইন: src_ip src_port dst_ip:port")
    args = p.parse_args(argv)

    try:
        if args.cmd == "lookup":
            routes = parse_routes(args.routes.read_text(encoding="utf-8"))
            missing = 0
            for ip in args.ips:
                r = lookup(routes, ip)
                if r is None:
                    print(f"{ip:15} → no route (Network is unreachable)")
                    missing += 1
                elif r.kind != "unicast":
                    print(f"{ip:15} → {r.kind} via {r.dest} (packet dropped)")
                else:
                    # gateway নেই = on-link: Ethernet-এ গন্তব্যের নিজের MAC (ARP); tunnel-এ (wg0) ARP নেই
                    hop = f"gateway {r.via}" if r.via else "on-link (no gateway)"
                    print(f"{ip:15} → {r.dest} dev {r.dev} {hop} metric {r.metric}")
            return 1 if missing else 0
        lo, hi = (int(x) for x in args.ports.split("-"))
        nat = Nat(args.public, range(lo, hi + 1))
        for line in args.flows.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            src_ip, src_port, dst = line.split()
            pub_ip, pub_port = nat.outbound(src_ip, int(src_port), dst)
            print(f"{src_ip}:{src_port} → {dst}  becomes  {pub_ip}:{pub_port} → {dst}")
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
