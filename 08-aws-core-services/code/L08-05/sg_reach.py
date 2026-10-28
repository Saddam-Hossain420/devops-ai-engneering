#!/usr/bin/env python3
"""sg_reach.py — security group ও network ACL দিয়ে একটি TCP/UDP flow পৌঁছায় কিনা, কোন ধাপে আটকায়; offline।

  aws ec2 describe-security-groups --filters Name=vpc-id,Values=$V > security-groups.json
  aws ec2 describe-network-acls --filters Name=vpc-id,Values=$V > network-acls.json

  python3 sg_reach.py check security-groups.json network-acls.json --flows flows.json
  python3 sg_reach.py check security-groups.json network-acls.json \
      --src-ip 10.20.0.10 --src-sg sg-alb --src-subnet subnet-pub-a \
      --dst-ip 10.20.16.5 --dst-sg sg-app --dst-subnet subnet-app-a --port 8000
  python3 sg_reach.py audit security-groups.json

ধাপ (packet-এর ক্রমে): উৎসের SG egress → উৎস subnet-এর NACL outbound → গন্তব্য subnet-এর NACL inbound →
গন্তব্যের SG inbound → ফেরত পথ: গন্তব্য NACL outbound ও উৎস NACL inbound (client-এর ephemeral port-এ)।
SG stateful (ফেরত নিজে থেকে allowed); NACL stateless (ফেরতের নিয়ম আলাদা লাগে)। একই subnet-এর ভেতরে NACL প্রযোজ্য নয়।
উৎস VPC-র বাইরে (internet) হলে তার SG/NACL ধাপ বাদ। Exit: check — সব expect মিলেছে 0, নইলে 1; audit — CRITICAL থাকলে 1।
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROTO = {"tcp": "6", "udp": "17"}
SENSITIVE = {22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis", 27017: "MongoDB",
             9200: "Elasticsearch", 2375: "Docker API", 11211: "Memcached"}
ANYWHERE = ("0.0.0.0/0", "::/0")


@dataclass
class Flow:
    name: str
    src_ip: str
    dst_ip: str
    port: int
    proto: str = "tcp"
    src_sgs: list[str] = field(default_factory=list)
    src_subnet: str | None = None
    dst_sgs: list[str] = field(default_factory=list)
    dst_subnet: str | None = None
    src_port: int = 50000               # client-এর ephemeral port (Linux 32768–60999, ELB 1024–65535)
    expect: str | None = None


def ip_in(ip: str, cidr: str) -> bool:
    a, net = ipaddress.ip_address(ip), ipaddress.ip_network(cidr, strict=False)
    return a.version == net.version and a in net


def port_ok(rule: dict[str, Any], port: int) -> bool:
    if rule.get("IpProtocol") == "-1":
        return True
    return rule.get("FromPort", 0) <= port <= rule.get("ToPort", 65535)


def sg_allows(groups: dict[str, dict], sg_ids: list[str], direction: str, peer_ip: str, peer_sgs: list[str],
              port: int, proto: str) -> str | None:
    """কোনো rule মিললে তার বর্ণনা, নইলে None। direction: IpPermissions (inbound) বা IpPermissionsEgress।"""
    for sg_id in sg_ids:
        for rule in groups[sg_id].get(direction, []):
            if rule.get("IpProtocol") not in ("-1", proto, PROTO.get(proto)) or not port_ok(rule, port):
                continue
            for r in rule.get("IpRanges", []):
                if ip_in(peer_ip, r["CidrIp"]):
                    return f"{sg_id} {r['CidrIp']}"
            for r in rule.get("Ipv6Ranges", []):
                if ip_in(peer_ip, r["CidrIpv6"]):
                    return f"{sg_id} {r['CidrIpv6']}"
            for pair in rule.get("UserIdGroupPairs", []):
                if pair.get("GroupId") in peer_sgs:
                    return f"{sg_id} ← {pair['GroupId']}"
    return None


def acl_for(acls: list[dict], subnet: str) -> dict:
    for acl in acls:
        if any(a.get("SubnetId") == subnet for a in acl.get("Associations", [])):
            return acl
    default = [a for a in acls if a.get("IsDefault")]
    if not default:
        raise KeyError(f"no network ACL for {subnet}")
    return default[0]


def acl_decides(acl: dict, egress: bool, peer_ip: str, port: int, proto: str) -> tuple[bool, str]:
    """সবচেয়ে ছোট rule number আগে; প্রথম মিলই চূড়ান্ত। কিছু না মিললে deny (*)।"""
    for e in sorted((e for e in acl.get("Entries", []) if e.get("Egress") == egress), key=lambda e: e["RuleNumber"]):
        if e.get("Protocol") not in ("-1", PROTO.get(proto)):
            continue
        cidr = e.get("CidrBlock") or e.get("Ipv6CidrBlock")
        if not cidr or not ip_in(peer_ip, cidr):
            continue
        pr = e.get("PortRange")
        if e.get("Protocol") != "-1" and pr and not pr["From"] <= port <= pr["To"]:
            continue
        rn = "*" if e["RuleNumber"] == 32767 else e["RuleNumber"]
        return e["RuleAction"] == "allow", f"{acl['NetworkAclId']} rule {rn} {e['RuleAction']}"
    return False, f"{acl['NetworkAclId']} no matching rule (deny)"


def check(flow: Flow, groups: dict[str, dict], acls: list[dict]) -> list[tuple[bool, str]]:
    steps: list[tuple[bool, str]] = []
    cross = flow.src_subnet != flow.dst_subnet

    def add(ok: bool, what: str) -> bool:
        steps.append((ok, what))
        return ok

    if flow.src_sgs:
        hit = sg_allows(groups, flow.src_sgs, "IpPermissionsEgress", flow.dst_ip, flow.dst_sgs, flow.port, flow.proto)
        if not add(hit is not None, f"source SG egress to {flow.dst_ip}:{flow.port}: {hit or 'no rule'}"):
            return steps
    if flow.src_subnet and cross:
        ok, why = acl_decides(acl_for(acls, flow.src_subnet), True, flow.dst_ip, flow.port, flow.proto)
        if not add(ok, f"source NACL outbound: {why}"):
            return steps
    if flow.dst_subnet and cross:
        ok, why = acl_decides(acl_for(acls, flow.dst_subnet), False, flow.src_ip, flow.port, flow.proto)
        if not add(ok, f"destination NACL inbound: {why}"):
            return steps
    hit = sg_allows(groups, flow.dst_sgs, "IpPermissions", flow.src_ip, flow.src_sgs, flow.port, flow.proto)
    if not add(hit is not None, f"destination SG inbound from {flow.src_ip}: {hit or 'no rule'}"):
        return steps
    if flow.dst_subnet and cross:
        ok, why = acl_decides(acl_for(acls, flow.dst_subnet), True, flow.src_ip, flow.src_port, flow.proto)
        if not add(ok, f"return: destination NACL outbound to port {flow.src_port}: {why}"):
            return steps
    if flow.src_subnet and cross:
        ok, why = acl_decides(acl_for(acls, flow.src_subnet), False, flow.dst_ip, flow.src_port, flow.proto)
        add(ok, f"return: source NACL inbound on port {flow.src_port}: {why}")
    return steps


def audit(groups: dict[str, dict]) -> list[tuple[str, str, str]]:
    out = []
    for sg_id, g in groups.items():
        for rule in g.get("IpPermissions", []):
            cidrs = [r["CidrIp"] for r in rule.get("IpRanges", [])] + [r["CidrIpv6"] for r in rule.get("Ipv6Ranges", [])]
            open_world = [c for c in cidrs if c in ANYWHERE]
            if open_world and rule.get("IpProtocol") == "-1":
                out.append(("CRITICAL", sg_id, f"all traffic from {open_world[0]}"))
                continue
            for port, svc in SENSITIVE.items():
                if open_world and port_ok(rule, port):
                    out.append(("CRITICAL", sg_id, f"{svc} ({port}) open to {open_world[0]} — use SSM Session Manager "
                                                   "or a source-restricted rule"))
            if open_world and rule.get("FromPort") not in (80, 443) and rule.get("ToPort", 0) - rule.get("FromPort", 0) > 0:
                out.append(("WARN", sg_id, f"port range {rule['FromPort']}-{rule['ToPort']} open to {open_world[0]}"))
            for pair in rule.get("UserIdGroupPairs", []):
                if pair.get("GroupId") not in groups:
                    out.append(("WARN", sg_id, f"references {pair['GroupId']}, not in this input (deleted? another VPC?)"))
    return out


def load_flows(a: argparse.Namespace) -> list[Flow]:
    if a.flows:
        return [Flow(**f) for f in json.loads(a.flows.read_text(encoding="utf-8"))]
    if not (a.src_ip and a.dst_ip and a.port):
        raise ValueError("give --flows FILE or --src-ip, --dst-ip and --port")
    return [Flow("flow", a.src_ip, a.dst_ip, a.port, a.proto, a.src_sg, a.src_subnet, a.dst_sg, a.dst_subnet,
                 a.src_port)]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Security group + NACL reachability (offline).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("sgs", type=Path)
    c.add_argument("acls", type=Path)
    c.add_argument("--flows", type=Path)
    c.add_argument("--src-ip")
    c.add_argument("--src-sg", action="append", default=[])
    c.add_argument("--src-subnet")
    c.add_argument("--dst-ip")
    c.add_argument("--dst-sg", action="append", default=[])
    c.add_argument("--dst-subnet")
    c.add_argument("--port", type=int)
    c.add_argument("--proto", choices=sorted(PROTO), default="tcp")
    c.add_argument("--src-port", type=int, default=50000)
    au = sub.add_parser("audit")
    au.add_argument("sgs", type=Path)
    a = ap.parse_args(argv)
    try:
        groups = {g["GroupId"]: g for g in json.loads(a.sgs.read_text(encoding="utf-8"))["SecurityGroups"]}
        if a.cmd == "audit":
            findings = audit(groups)
            for lvl, sg_id, msg in sorted(findings, key=lambda f: (f[0] != "CRITICAL", f[1])):
                print(f"{lvl:<8}  {sg_id:<10} {msg}")
            print(f"{len(groups)} security group(s), {len(findings)} finding(s)")
            return 1 if any(f[0] == "CRITICAL" for f in findings) else 0
        acls = json.loads(a.acls.read_text(encoding="utf-8"))["NetworkAcls"]
        flows = load_flows(a)
        mismatches = 0
        for f in flows:
            missing = [s for s in f.src_sgs + f.dst_sgs if s not in groups]
            if missing:
                raise KeyError(f"{f.name}: unknown security group {missing}")
            steps = check(f, groups, acls)
            allowed = all(ok for ok, _ in steps)
            verdict = "ALLOW" if allowed else "DROP "
            flag = ""
            if f.expect:
                good = (f.expect == "allow") == allowed
                mismatches += not good
                flag = "  ✓ as expected" if good else f"  ✗ expected {f.expect}"
            print(f"{verdict}  {f.name}{flag}")
            for ok, what in steps:
                print(f"         {'ok ' if ok else 'XX '} {what}")
            if not allowed:
                print("         → client sees a TIMEOUT (dropped silently), not 'connection refused'")
        print(f"{len(flows)} flow(s), {mismatches} unexpected")
        return 1 if mismatches else 0
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
