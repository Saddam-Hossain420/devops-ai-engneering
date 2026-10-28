#!/usr/bin/env python3
"""VPC simulator — subnet, route table, internet/NAT gateway, peering; reachability trace ও design lint।
কোনো cloud API call নেই, কোনো resource তৈরি হয় না, খরচ শূন্য।

  python3 vpc_sim.py lint sample-vpcs.json
  python3 vpc_sim.py trace sample-vpcs.json --from api-1 --to 1.1.1.1
  python3 vpc_sim.py trace sample-vpcs.json --from api-1 --to 10.1.3.10

Model AWS-এর ধারণা অনুসরণ করে (প্রতিটি route table-এ implicit "local" route, peering non-transitive,
NAT gateway public subnet-এ)। Security group/NACL এখানে নেই — সেগুলো L02-10।
Exit: lint → 0 পরিষ্কার / 1 finding; trace → 0 পৌঁছায় / 1 পৌঁছায় না; 2 input error।
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path

IPNet = ipaddress.IPv4Network


class Model:
    def __init__(self, spec: dict) -> None:
        self.spec = spec
        self.vpcs = spec["vpcs"]
        self.peerings: dict[str, list[str]] = spec.get("peerings", {})
        self.instances = spec.get("instances", {})
        self.subnet_vpc = {s: v for v, vpc in self.vpcs.items() for s in vpc["subnets"]}

    def cidr(self, vpc: str) -> IPNet:
        return ipaddress.ip_network(self.vpcs[vpc]["cidr"])

    def subnet(self, name: str) -> dict:
        return self.vpcs[self.subnet_vpc[name]]["subnets"][name]

    def routes(self, subnet: str) -> list[tuple[IPNet, str]]:
        vpc = self.subnet_vpc[subnet]
        table = self.vpcs[vpc]["route_tables"][self.subnet(subnet)["route_table"]]
        out = [(self.cidr(vpc), "local")]  # প্রতিটি route table-এ implicit, মোছা যায় না
        out += [(ipaddress.ip_network(r["dest"]), r["target"]) for r in table]
        return out

    def lookup(self, subnet: str, ip: str) -> tuple[IPNet, str] | None:
        addr = ipaddress.ip_address(ip)
        matches = [r for r in self.routes(subnet) if addr in r[0]]
        return max(matches, key=lambda r: r[0].prefixlen) if matches else None  # longest prefix (L02-04)

    def subnet_of_ip(self, vpc: str, ip: str) -> str | None:
        addr = ipaddress.ip_address(ip)
        return next((s for s, d in self.vpcs[vpc]["subnets"].items() if addr in ipaddress.ip_network(d["cidr"])), None)

    def has_igw_default(self, subnet: str) -> bool:
        r = self.lookup(subnet, "1.1.1.1")
        return r is not None and r[1] == "igw"


def trace(m: Model, src: str, dest: str) -> tuple[bool, list[str]]:
    inst = m.instances[src]
    subnet, ip = inst["subnet"], inst["ip"]
    vpc = m.subnet_vpc[subnet]
    hops = [f"{src} {ip} in {subnet} ({vpc}, AZ {m.subnet(subnet)['az']})"]
    route = m.lookup(subnet, dest)
    if route is None:
        return False, hops + [f"route table '{m.subnet(subnet)['route_table']}': no route to {dest} → dropped"]
    net, target = route
    hops.append(f"route table '{m.subnet(subnet)['route_table']}': {dest} matches {net} → {target}")

    if target == "local":
        dsub = m.subnet_of_ip(vpc, dest)
        if dsub is None:
            return False, hops + [f"{dest} is inside {vpc} CIDR but in no subnet → nothing there"]
        return True, hops + [f"delivered inside {vpc} to subnet {dsub} (security group/NACL still apply)"]

    if target == "igw":
        if not m.vpcs[vpc].get("igw"):
            return False, hops + [f"{vpc} has no internet gateway attached → blackhole"]
        if not inst.get("public_ip"):
            return False, hops + ["instance has no public IP: the internet gateway cannot translate it → dropped "
                                  "(private instances need a NAT gateway)"]
        return True, hops + [f"internet gateway: {ip} ↔ its public IP (1:1 NAT) → internet"]

    if target.startswith("nat:"):
        nat = target[4:]
        ng = m.vpcs[vpc].get("nat_gateways", {}).get(nat)
        if ng is None:
            return False, hops + [f"NAT gateway {nat} does not exist → blackhole"]
        hops.append(f"NAT gateway {nat} in {ng['subnet']} (AZ {m.subnet(ng['subnet'])['az']}): "
                    f"source {ip} → NAT's public IP")
        if not m.has_igw_default(ng["subnet"]):
            return False, hops + [f"NAT's subnet {ng['subnet']} has no default route to an internet gateway → dropped"]
        return True, hops + ["internet gateway → internet (replies come back through the NAT; "
                             "inbound connections from the internet are not possible)"]

    if target.startswith("pcx:"):
        pcx = target[4:]
        pair = m.peerings.get(pcx)
        if not pair or vpc not in pair:
            return False, hops + [f"peering {pcx} does not exist or does not include {vpc} → blackhole"]
        peer = pair[1] if pair[0] == vpc else pair[0]
        if ipaddress.ip_address(dest) not in m.cidr(peer):
            return False, hops + [f"{dest} is not in {peer}'s CIDR {m.cidr(peer)}: peering is NOT transitive → dropped"]
        dsub = m.subnet_of_ip(peer, dest)
        if dsub is None:
            return False, hops + [f"{dest} is in {peer} but in no subnet"]
        hops.append(f"via peering {pcx} into {peer}, subnet {dsub}")
        back = m.lookup(dsub, ip)
        if back is None or back[1] != f"pcx:{pcx}":
            got = "no route" if back is None else f"{back[0]} → {back[1]}"
            return False, hops + [f"return path broken: {dsub}'s route table '{m.subnet(dsub)['route_table']}' "
                                  f"has {got} for {ip} → replies never come back (one-way)"]
        return True, hops + [f"return route in '{m.subnet(dsub)['route_table']}' via {pcx} ✓ — delivered"]

    return False, hops + [f"unknown target {target!r}"]


def lint(m: Model) -> list[str]:
    out: list[str] = []
    for pcx, (a, b) in m.peerings.items():
        if m.cidr(a).overlaps(m.cidr(b)):
            out.append(f"ERROR peering {pcx}: {a} {m.cidr(a)} overlaps {b} {m.cidr(b)} — peering cannot route overlapping CIDRs")
    for v in m.vpcs:
        peers = sorted({x for pair in m.peerings.values() if v in pair for x in pair if x != v})
        for i, a in enumerate(peers):
            for b in peers[i + 1:]:
                if m.cidr(a).overlaps(m.cidr(b)):
                    out.append(f"ERROR {v} peers with both {a} and {b}, whose CIDRs overlap ({m.cidr(a)}) — "
                               f"{v} cannot route to both; plan non-overlapping CIDRs up front")
    for v, vpc in m.vpcs.items():
        seen: list[tuple[IPNet, str]] = []
        for s, d in vpc["subnets"].items():
            net = ipaddress.ip_network(d["cidr"])
            if not net.subnet_of(m.cidr(v)):
                out.append(f"ERROR subnet {s} {net} is outside {v} {m.cidr(v)}")
            for other, oname in seen:
                if net.overlaps(other):
                    out.append(f"ERROR subnet {s} {net} overlaps {oname} {other}")
            seen.append((net, s))
            if d["route_table"] not in vpc["route_tables"]:
                out.append(f"ERROR subnet {s} uses missing route table {d['route_table']}")
        for rt, routes in vpc["route_tables"].items():
            for r in routes:
                t = r["target"]
                if t == "igw" and not vpc.get("igw"):
                    out.append(f"ERROR {v}/{rt}: route to igw but {v} has no internet gateway")
                elif t.startswith("nat:") and t[4:] not in vpc.get("nat_gateways", {}):
                    out.append(f"ERROR {v}/{rt}: NAT gateway {t[4:]} does not exist")
                elif t.startswith("pcx:") and v not in m.peerings.get(t[4:], []):
                    out.append(f"ERROR {v}/{rt}: peering {t[4:]} does not include {v}")
        nat_azs: dict[str, set[str]] = {}
        for nat, ng in vpc.get("nat_gateways", {}).items():
            if not m.has_igw_default(ng["subnet"]):
                out.append(f"ERROR {v}: NAT gateway {nat} sits in {ng['subnet']}, which has no route to an internet gateway")
            for s, d in vpc["subnets"].items():
                r = m.lookup(s, "1.1.1.1")
                if r and r[1] == f"nat:{nat}":
                    nat_azs.setdefault(nat, set()).add(d["az"])
        for nat, azs in nat_azs.items():
            if len(azs) > 1:
                out.append(f"WARN  {v}: NAT gateway {nat} serves subnets in AZs {sorted(azs)} — one AZ outage cuts "
                           "egress for all, and cross-AZ traffic is billed; use one NAT per AZ")
    for name, inst in m.instances.items():
        if inst.get("public_ip") and not m.has_igw_default(inst["subnet"]):
            out.append(f"WARN  instance {name} has a public IP but its subnet has no route to an internet gateway")
        if inst.get("public_ip") and m.subnet(inst["subnet"]).get("tier") in ("app", "data"):
            out.append(f"WARN  instance {name} in {m.subnet(inst['subnet'])['tier']} tier has a public IP")
    return out


def load(path: Path) -> Model:
    m = Model(json.loads(path.read_text(encoding="utf-8")))
    for name, inst in m.instances.items():
        if inst["subnet"] not in m.subnet_vpc:
            raise ValueError(f"instance {name}: unknown subnet {inst['subnet']}")
    return m


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Offline VPC reachability and design checks.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("lint")
    l.add_argument("spec", type=Path)
    t = sub.add_parser("trace")
    t.add_argument("spec", type=Path)
    t.add_argument("--from", dest="src", required=True)
    t.add_argument("--to", dest="dest", required=True)
    args = ap.parse_args(argv)
    try:
        m = load(args.spec)
        if args.cmd == "lint":
            findings = lint(m)
            for f in findings:
                print(f)
            print(f"{len(m.vpcs)} VPC(s), {len(m.subnet_vpc)} subnet(s), {len(findings)} finding(s)")
            return 1 if findings else 0
        if args.src not in m.instances:
            raise ValueError(f"unknown instance {args.src}")
        ipaddress.ip_address(args.dest)
        ok, hops = trace(m, args.src, args.dest)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for i, h in enumerate(hops):
        print(f"{'  ' * min(i, 1)}{'→ ' if i else ''}{h}")
    print("REACHABLE" if ok else "NOT REACHABLE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
