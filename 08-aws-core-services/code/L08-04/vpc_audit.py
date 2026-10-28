#!/usr/bin/env python3
"""vpc_audit.py — একটি VPC-র subnet কোনটা public/private/isolated, এবং routing-এর ভুল; AWS CLI output থেকে (offline)।

  V=vpc-0123; F="--filters Name=vpc-id,Values=$V"
  aws ec2 describe-subnets $F > subnets.json
  aws ec2 describe-route-tables $F > route-tables.json
  aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=$V > nat-gateways.json
  aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=$V > internet-gateways.json
  python3 vpc_audit.py subnets.json route-tables.json nat-gateways.json internet-gateways.json

Subnet-এর ধরন ঠিক হয় তার route table দিয়ে (নাম দিয়ে নয়): 0.0.0.0/0 → igw = public, → nat = private, না থাকলে isolated।
খোঁজে: blackhole route · NAT private subnet-এ · অন্য AZ-এর NAT-এ নির্ভরতা · main route table-এ implicit subnet ·
main table-এ internet route · public নয় এমন subnet-এ auto public IP · IGW attached নয় · মুছে-ফেলা NAT-এ route।
Exit: 0 কোনো CRITICAL নেই, 1 আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CRIT, WARN = "CRITICAL", "WARN"
DEFAULT_ROUTES = ("0.0.0.0/0", "::/0")


@dataclass
class SubnetView:
    id: str
    name: str
    az: str
    cidr: str
    route_table: str
    implicit: bool
    kind: str          # public / private / isolated
    via: str


def merge(docs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for d in docs:
        for k, v in d.items():
            if isinstance(v, list):
                out.setdefault(k, []).extend(v)
    return out


def name_of(item: dict[str, Any]) -> str:
    return next((t["Value"] for t in item.get("Tags", []) or [] if t["Key"] == "Name"), "")


def default_route(table: dict[str, Any]) -> dict[str, Any] | None:
    return next((r for r in table.get("Routes", [])
                 if r.get("DestinationCidrBlock") in DEFAULT_ROUTES or r.get("DestinationIpv6CidrBlock") in DEFAULT_ROUTES),
                None)


def classify(route: dict[str, Any] | None) -> tuple[str, str]:
    if route is None:
        return "isolated", "no default route"
    target = route.get("GatewayId") or route.get("NatGatewayId") or route.get("TransitGatewayId") \
        or route.get("NetworkInterfaceId") or route.get("VpcPeeringConnectionId") or "?"
    if route.get("State") == "blackhole":
        return "isolated", f"{target} (blackhole)"
    if target.startswith("igw-"):
        return "public", target
    if target.startswith(("nat-", "eni-", "tgw-")):
        return "private", target
    return "isolated", target


def audit(data: dict[str, list[dict[str, Any]]]) -> tuple[list[SubnetView], list[tuple[str, str, str]]]:
    subnets = {s["SubnetId"]: s for s in data.get("Subnets", [])}
    tables = data.get("RouteTables", [])
    nats = {n["NatGatewayId"]: n for n in data.get("NatGateways", [])}
    igws = {g["InternetGatewayId"]: g for g in data.get("InternetGateways", [])}
    findings: list[tuple[str, str, str]] = []

    explicit = {a["SubnetId"]: t for t in tables for a in t.get("Associations", []) if a.get("SubnetId")}
    mains = {t["VpcId"]: t for t in tables if any(a.get("Main") for a in t.get("Associations", []))}

    for t in tables:
        for r in t.get("Routes", []):
            dest = r.get("DestinationCidrBlock") or r.get("DestinationIpv6CidrBlock") or "?"
            if r.get("State") == "blackhole":
                findings.append((CRIT, t["RouteTableId"], f"blackhole route {dest} → "
                                 f"{r.get('NatGatewayId') or r.get('GatewayId') or r.get('NetworkInterfaceId')} "
                                 "(target deleted) — traffic is silently dropped"))
            gw = r.get("GatewayId", "")
            if gw.startswith("igw-") and gw in igws and not any(
                    a.get("VpcId") == t["VpcId"] and a.get("State") in ("available", "attached")
                    for a in igws[gw].get("Attachments", [])):
                findings.append((CRIT, t["RouteTableId"], f"route to {gw}, but it is not attached to {t['VpcId']}"))
        if t in mains.values():
            kind, via = classify(default_route(t))
            if kind == "public":
                findings.append((CRIT, t["RouteTableId"], f"MAIN route table has an internet route ({via}) — "
                                 "every subnet without its own table becomes public"))

    views: list[SubnetView] = []
    for sid, s in sorted(subnets.items(), key=lambda kv: (kv[1]["AvailabilityZone"], kv[1]["CidrBlock"])):
        table = explicit.get(sid) or mains.get(s["VpcId"])
        if table is None:
            findings.append((CRIT, sid, "no route table found (incomplete input?)"))
            continue
        kind, via = classify(default_route(table))
        v = SubnetView(sid, name_of(s), s["AvailabilityZone"], s["CidrBlock"], table["RouteTableId"],
                       sid not in explicit, kind, via)
        views.append(v)
        if v.implicit:
            findings.append((WARN, sid, f"uses the main route table implicitly — associate it explicitly "
                                        f"({kind} today, changes if someone edits the main table)"))
        if s.get("MapPublicIpOnLaunch") and kind != "public":
            findings.append((WARN, sid, f"MapPublicIpOnLaunch=true on a {kind} subnet — instances get public IPs "
                                        "(billed) that cannot be used"))
        if via.startswith("nat-") and via in nats:
            nat = nats[via]
            nat_subnet = subnets.get(nat["SubnetId"])
            if nat.get("State") != "available":
                findings.append((CRIT, sid, f"default route via {via}, which is {nat.get('State')}"))
            elif nat_subnet and nat_subnet["AvailabilityZone"] != s["AvailabilityZone"]:
                findings.append((WARN, sid, f"uses {via} in {nat_subnet['AvailabilityZone']} — if that AZ fails this "
                                            "subnet loses internet; cross-AZ data is billed"))

    view_by_id = {v.id: v for v in views}
    for nid, n in nats.items():
        if n.get("State") in ("deleted", "failed") or n.get("ConnectivityType") == "private":
            continue
        home = view_by_id.get(n["SubnetId"])
        if home and home.kind != "public":
            findings.append((CRIT, nid, f"public NAT gateway sits in {home.kind} subnet {home.id} — it cannot reach "
                                        "the internet; put it in a public subnet"))
    return views, findings


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Classify subnets and audit VPC routing (offline).")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        views, findings = audit(merge([json.loads(p.read_text(encoding="utf-8")) for p in a.files]))
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"subnets": [vars(v) for v in views],
                          "findings": [{"level": lvl, "id": i, "message": m} for lvl, i, m in findings]}, indent=2))
    else:
        print(f"{'subnet':<16} {'name':<10} {'az':<12} {'cidr':<16} {'kind':<9} via")
        for v in views:
            rt = f"{v.route_table}{' (main, implicit)' if v.implicit else ''}"
            print(f"{v.id:<16} {v.name:<10} {v.az:<12} {v.cidr:<16} {v.kind:<9} {v.via}  [{rt}]")
        print()
        for lvl, i, m in sorted(findings, key=lambda f: (f[0] != CRIT, f[1])):
            print(f"{lvl:<8}  {i:<16} {m}")
        crit = sum(f[0] == CRIT for f in findings)
        print(f"{len(views)} subnet(s): {crit} critical, {len(findings) - crit} warning(s)")
    return 1 if any(f[0] == CRIT for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
