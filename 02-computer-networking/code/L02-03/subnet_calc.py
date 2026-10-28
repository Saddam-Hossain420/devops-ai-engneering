#!/usr/bin/env python3
"""Subnet calculator — IPv4/IPv6 CIDR তথ্য, ভাগ, overlap ও VPC subnet পরিকল্পনা (standard library `ipaddress`)।

Commands:
  python3 subnet_calc.py info 10.0.1.0/24
  python3 subnet_calc.py info 2001:db8:abcd::/48
  python3 subnet_calc.py split 10.0.0.0/16 --new-prefix 20
  python3 subnet_calc.py overlap 10.0.0.0/16 10.0.128.0/17 192.168.0.0/16
  python3 subnet_calc.py contains 10.0.1.0/24 10.0.1.77
  python3 subnet_calc.py plan 10.20.0.0/16 --azs 3 --tiers public,private,database --prefix 20
"""
from __future__ import annotations

import argparse
import ipaddress
import itertools
import sys

CLOUD_RESERVED = 5  # AWS: প্রথম ৪টি (network, VPC router, DNS, ভবিষ্যৎ) ও শেষটি (broadcast) ব্যবহার করা যায় না


def classify(net: ipaddress._BaseNetwork) -> str:
    if net.is_loopback:
        return "loopback"
    if net.is_link_local:
        return "link-local"
    if net.version == 4 and net.subnet_of(ipaddress.ip_network("100.64.0.0/10")):
        return "shared (CGNAT, RFC 6598)"
    if net.is_private:
        return "private (RFC 1918 / ULA / documentation)"
    if net.is_multicast:
        return "multicast"
    return "global (public)"


def info(cidr: str) -> dict[str, object]:
    net = ipaddress.ip_network(cidr, strict=False)
    hosts = net.num_addresses
    out: dict[str, object] = {"network": str(net), "version": net.version, "addresses": hosts,
                              "type": classify(net)}
    if net.version == 4:
        usable = hosts - 2 if net.prefixlen <= 30 else hosts  # /31 point-to-point, /32 single host
        out.update({
            "netmask": str(net.netmask),
            "wildcard": str(net.hostmask),
            "broadcast": str(net.broadcast_address) if net.prefixlen <= 30 else "-",
            "first_usable": str(net[1] if net.prefixlen <= 30 else net[0]),
            "last_usable": str(net[-2] if net.prefixlen <= 30 else net[-1]),
            "usable_hosts": usable,
            "usable_in_aws_subnet": max(hosts - CLOUD_RESERVED, 0) if 16 <= net.prefixlen <= 28 else "n/a (AWS subnet /16–/28)",
        })
    else:
        out.update({"first": str(net[0]), "last": str(net[-1]),
                    "/64 subnets inside": 2 ** (64 - net.prefixlen) if net.prefixlen <= 64 else "n/a"})
    return out


def split(cidr: str, new_prefix: int) -> list[str]:
    net = ipaddress.ip_network(cidr)
    if new_prefix <= net.prefixlen:
        raise ValueError(f"new prefix /{new_prefix} must be longer than /{net.prefixlen}")
    return [str(s) for s in net.subnets(new_prefix=new_prefix)]


def overlaps(cidrs: list[str]) -> list[tuple[str, str]]:
    nets = [ipaddress.ip_network(c) for c in cidrs]
    return [(str(a), str(b)) for a, b in itertools.combinations(nets, 2)
            if a.version == b.version and a.overlaps(b)]


def plan(vpc: str, azs: int, tiers: list[str], prefix: int) -> list[tuple[str, str, str]]:
    """প্রতিটি tier × AZ-এর জন্য ক্রমানুসারে subnet। জায়গা না থাকলে ValueError।"""
    pool = split(vpc, prefix)
    need = azs * len(tiers)
    if need > len(pool):
        raise ValueError(f"need {need} subnets of /{prefix} but {vpc} has only {len(pool)}")
    rows = []
    it = iter(pool)
    for tier in tiers:
        for az in range(azs):
            rows.append((tier, f"az-{chr(ord('a') + az)}", next(it)))
    return rows


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="IPv4/IPv6 subnet calculator.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info").add_argument("cidr")
    s = sub.add_parser("split")
    s.add_argument("cidr")
    s.add_argument("--new-prefix", type=int, required=True)
    sub.add_parser("overlap").add_argument("cidrs", nargs="+")
    c = sub.add_parser("contains")
    c.add_argument("cidr")
    c.add_argument("ip")
    pl = sub.add_parser("plan")
    pl.add_argument("vpc")
    pl.add_argument("--azs", type=int, default=3)
    pl.add_argument("--tiers", default="public,private,database")
    pl.add_argument("--prefix", type=int, default=20)
    args = p.parse_args(argv)

    try:
        if args.cmd == "info":
            for k, v in info(args.cidr).items():
                print(f"{k:22} {v}")
        elif args.cmd == "split":
            subs = split(args.cidr, args.new_prefix)
            for x in subs[:16]:
                print(x)
            if len(subs) > 16:
                print(f"... ({len(subs)} subnets total)")
        elif args.cmd == "overlap":
            found = overlaps(args.cidrs)
            for a, b in found:
                print(f"OVERLAP {a} ↔ {b}")
            print("no overlaps" if not found else f"{len(found)} overlap(s)")
            return 1 if found else 0
        elif args.cmd == "contains":
            inside = ipaddress.ip_address(args.ip) in ipaddress.ip_network(args.cidr, strict=False)
            print(f"{args.ip} {'is' if inside else 'is NOT'} in {args.cidr}")
            return 0 if inside else 1
        else:
            for tier, az, net in plan(args.vpc, args.azs, args.tiers.split(","), args.prefix):
                n = ipaddress.ip_network(net)
                print(f"{tier:10} {az}  {net:18} usable (AWS) {n.num_addresses - CLOUD_RESERVED}")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
