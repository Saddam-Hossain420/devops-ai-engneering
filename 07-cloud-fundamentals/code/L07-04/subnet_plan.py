#!/usr/bin/env python3
"""subnet_plan.py — VPC CIDR থেকে multi-AZ subnet পরিকল্পনা (public / private / isolated), সংঘাত ও ভবিষ্যতের জায়গা যাচাই।

  python3 subnet_plan.py plan.json
  python3 subnet_plan.py plan.json --json

plan.json: {"vpc": "10.20.0.0/16", "azs": ["a","b","c"], "reserved_per_subnet": 5,
            "avoid": {"on-prem": "10.0.0.0/12", "peer-vpc": "10.30.0.0/16"},
            "tiers": [{"name": "public", "type": "public", "hosts": 60}, ...]}
type: public (internet gateway; ingress সম্ভব), private (NAT দিয়ে শুধু বাইরে যাওয়া), isolated (internet নেই)।
reserved_per_subnet: provider প্রতিটি subnet-এ কয়টি address নিজে রাখে — AWS-এ ৫ (documentation দেখুন)।
বড় subnet আগে, প্রতিটি AZ-এ একই আকার, prefix-এর সীমায় align। কোনো API call নেই।
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROUTES = {"public": "0.0.0.0/0 → internet gateway (public IP থাকলে ingress সম্ভব)",
          "private": "0.0.0.0/0 → NAT gateway in a public subnet (শুধু outbound; NAT-এর data খরচ)",
          "isolated": "শুধু VPC-র local route (internet নেই; object storage-এ private endpoint)"}


class PlanError(Exception):
    pass


@dataclass
class Subnet:
    tier: str
    type: str
    az: str
    cidr: str
    usable: int


def prefix_for(hosts: int, reserved: int) -> int:
    """hosts-সংখ্যক ব্যবহারযোগ্য address পেতে সবচেয়ে ছোট prefix (reserved বাদ দিয়ে)।"""
    need = hosts + reserved
    prefix = 32 - math.ceil(math.log2(max(need, 2)))
    if prefix < 16:
        raise PlanError(f"{hosts} hosts need a subnet larger than /16")
    return min(prefix, 28)                          # অনেক provider-এর ক্ষুদ্রতম subnet /28


def plan(spec: dict) -> tuple[list[Subnet], list[str]]:
    vpc = ipaddress.ip_network(spec["vpc"])
    reserved = spec.get("reserved_per_subnet", 5)
    if not (16 <= vpc.prefixlen <= 28):
        raise PlanError(f"VPC {vpc} must be between /16 and /28")
    for label, cidr in spec.get("avoid", {}).items():
        other = ipaddress.ip_network(cidr)
        if vpc.overlaps(other):
            raise PlanError(f"VPC {vpc} overlaps {label} {other} — peering/VPN routing will be ambiguous; pick another range")
    if not vpc.is_private:
        raise PlanError(f"VPC {vpc} is not an RFC 1918 / private range")
    requests = []
    for tier in spec["tiers"]:
        if tier["type"] not in ROUTES:
            raise PlanError(f"tier {tier['name']}: unknown type {tier['type']!r}")
        p = prefix_for(tier["hosts"], reserved)
        requests += [(p, tier, az) for az in spec["azs"]]
    requests.sort(key=lambda r: (r[0], spec["tiers"].index(r[1]), r[2]))      # বড় (ছোট prefix) আগে
    free = [vpc]
    subnets: list[Subnet] = []
    for prefix, tier, az in requests:
        # সবচেয়ে ছোট যে free block-এ আঁটে (best fit) — বড় block ভবিষ্যতের জন্য অক্ষত থাকে
        for block in sorted(free, key=lambda n: (n.prefixlen, int(n.network_address)), reverse=True):
            if block.prefixlen <= prefix:
                free.remove(block)
                chosen = next(block.subnets(new_prefix=prefix))          # block-এর প্রথম, prefix-এ aligned অংশ
                free += list(block.address_exclude(chosen)) if block != chosen else []   # বাকিটা ফেরত
                subnets.append(Subnet(tier["name"], tier["type"], az, str(chosen), chosen.num_addresses - reserved))
                break
        else:
            raise PlanError(f"VPC {vpc} has no room left for {tier['name']} in AZ {az} (/{prefix})")
    subnets.sort(key=lambda s: ipaddress.ip_network(s.cidr))
    left = sum(n.num_addresses for n in free)
    notes = [f"unallocated: {left} addresses ({left * 100 // vpc.num_addresses}% of the VPC) kept for growth"]
    if left < vpc.num_addresses // 4:
        notes.append("less than 25% left — containers/Kubernetes pods (one IP each) can exhaust this quickly")
    if any(t["type"] == "private" for t in spec["tiers"]) and not any(t["type"] == "public" for t in spec["tiers"]):
        notes.append("private tier needs a NAT gateway, which must live in a public subnet — none planned")
    return subnets, notes


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Plan multi-AZ subnets from a VPC CIDR.")
    ap.add_argument("plan", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        spec = json.loads(a.plan.read_text(encoding="utf-8"))
        subnets, notes = plan(spec)
    except (OSError, KeyError, ValueError, PlanError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if isinstance(exc, PlanError) else 2
    if a.json:
        print(json.dumps({"subnets": [asdict(s) for s in subnets], "notes": notes}, indent=2, ensure_ascii=False))
        return 0
    print(f"{'tier':<10} {'type':<9} {'az':<4} {'cidr':<18} usable")
    for s in subnets:
        print(f"{s.tier:<10} {s.type:<9} {s.az:<4} {s.cidr:<18} {s.usable}")
    print()
    for t in dict.fromkeys(s.type for s in subnets):
        print(f"route ({t}): {ROUTES[t]}")
    for n in notes:
        print(f"note: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
