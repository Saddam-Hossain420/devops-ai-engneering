#!/usr/bin/env python3
"""Lab 08-B verification — TaskFlow: নিজের VPC → private subnet-এ দুটি EC2 → ALB (offline, saved describe output থেকে)।

  python3 check_b.py ~/lab08b
  python3 check_b.py ~/lab08b --after-cleanup

Module 08-এর tool একসাথে: vpc_audit (L08-04), sg_reach (L08-05), ec2_audit (L08-06), tg_health (L08-09)।
Flow-গুলো input থেকেই বের হয়: ALB-এর subnet ও SG `load-balancers.json` থেকে, instance-এর IP/subnet/SG
`instances.json` থেকে। ALB-এর প্রতিটি subnet থেকে প্রতিটি instance-এ পথ পরীক্ষা হয় (AZ-ভেদে NACL আলাদা হতে পারে)।
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
for sub in ("L08-04", "L08-05", "L08-06", "L08-09"):
    sys.path.insert(0, str(REPO / "08-aws-core-services" / "code" / sub))
import ec2_audit as ea  # noqa: E402
import sg_reach as sr  # noqa: E402
import tg_health as th  # noqa: E402
import vpc_audit as va  # noqa: E402

INTERNET = "198.51.100.7"            # documentation address (RFC 5737) — "internet-এর কেউ"


def load(folder: Path, name: str) -> dict[str, Any]:
    return json.loads((folder / name).read_text(encoding="utf-8"))


def representative_ip(cidr: str) -> str:
    return str(ipaddress.ip_network(cidr)[10])          # subnet-এর ভেতরের একটি ঠিকানা — ALB node-এর প্রতিনিধি


def check(folder: Path) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    vpc = va.merge([load(folder, f) for f in ("subnets.json", "route-tables.json", "nat-gateways.json",
                                               "internet-gateways.json")])
    views, vfind = va.audit(vpc)
    crit = [f"{i}: {m}" for lvl, i, m in vfind if lvl == va.CRIT]
    out.append((not crit, "vpc_audit: no CRITICAL" + ("" if not crit else f" — {crit[0]}")))
    kind = {v.id: v for v in views}
    cidr = {s["SubnetId"]: s["CidrBlock"] for s in vpc["Subnets"]}

    lb = load(folder, "load-balancers.json")["LoadBalancers"][0]
    lb_subnets = [z["SubnetId"] for z in lb["AvailabilityZones"]]
    out.append((lb.get("Scheme") == "internet-facing" and lb.get("State", {}).get("Code") == "active",
                f"ALB {lb.get('LoadBalancerName')} is internet-facing and active"))
    out.append((all(kind[s].kind == "public" for s in lb_subnets if s in kind) and len(lb_subnets) >= 2,
                f"ALB in ≥2 public subnets ({', '.join(f'{s}:{kind[s].kind}' for s in lb_subnets if s in kind)})"))

    instances = [i for i in ea.instances_of(load(folder, "instances.json")) if i["State"]["Name"] == "running"]
    azs = {kind[i["SubnetId"]].az for i in instances if i["SubnetId"] in kind}
    out.append((len(instances) >= 2 and len(azs) >= 2, f"≥2 running instances in ≥2 AZs ({len(instances)} in {sorted(azs)})"))
    for i in instances:
        k = kind.get(i["SubnetId"])
        out.append((k is not None and k.kind != "public" and not i.get("PublicIpAddress"),
                    f"{i['InstanceId']}: private subnet, no public IP ({k.kind if k else '?'})"))
    efind = [f"{iid}: {m}" for lvl, iid, m in ea.audit(instances, ["Project"]) if lvl == "CRITICAL"]
    out.append((not efind, "ec2_audit: no CRITICAL" + ("" if not efind else f" — {efind[0]}")))
    imds = all(i.get("MetadataOptions", {}).get("HttpTokens") == "required" for i in instances)
    out.append((imds, "IMDSv2 required on every instance"))

    groups = {g["GroupId"]: g for g in load(folder, "security-groups.json")["SecurityGroups"]}
    acls = load(folder, "network-acls.json")["NetworkAcls"]
    sfind = [f"{g}: {m}" for lvl, g, m in sr.audit(groups) if lvl == "CRITICAL"]
    out.append((not sfind, "sg_reach audit: no CRITICAL" + ("" if not sfind else f" — {sfind[0]}")))
    alb_sgs = lb.get("SecurityGroups", [])
    for s in lb_subnets[:1]:
        f = sr.Flow("internet→ALB", INTERNET, representative_ip(cidr[s]), 80, dst_sgs=alb_sgs, dst_subnet=s)
        out.append((all(ok for ok, _ in sr.check(f, groups, acls)), "internet → ALB :80 allowed"))
    for i in instances:
        app_sgs = [g["GroupId"] for g in i.get("SecurityGroups", [])]
        open_world = [r for g in app_sgs for r in groups[g].get("IpPermissions", [])
                      if any(x["CidrIp"] in ("0.0.0.0/0",) for x in r.get("IpRanges", []))]
        out.append((not open_world, f"{i['InstanceId']}: app security group has no 0.0.0.0/0 inbound"))
        for s in lb_subnets:
            f = sr.Flow("alb→app", representative_ip(cidr[s]), i["PrivateIpAddress"], 8000, src_sgs=alb_sgs,
                        src_subnet=s, dst_sgs=app_sgs, dst_subnet=i["SubnetId"])
            steps = sr.check(f, groups, acls)
            ok = all(o for o, _ in steps)
            out.append((ok, f"ALB ({s}) → {i['InstanceId']}:8000 allowed" + ("" if ok else f" — {steps[-1][1]}")))
        for port in (8000, 22):
            f = sr.Flow("internet→app", INTERNET, i["PrivateIpAddress"], port, dst_sgs=app_sgs, dst_subnet=i["SubnetId"])
            out.append((not all(o for o, _ in sr.check(f, groups, acls)), f"internet → {i['InstanceId']}:{port} blocked"))

    tg = load(folder, "tg.json")["TargetGroups"][0]
    out.append((tg.get("HealthCheckPath") == "/health" and tg.get("Port") == 8000,
                f"target group checks /health on 8000 ({tg.get('HealthCheckPath')} :{tg.get('Port')})"))
    health = load(folder, "health.json")["TargetHealthDescriptions"]
    states = {d["Target"]["Id"]: d["TargetHealth"]["State"] for d in health}
    out.append((set(states) == {i["InstanceId"] for i in instances} and set(states.values()) == {"healthy"},
                f"every instance registered and healthy ({states})"))
    warn = [m for lvl, m in th.check_settings(tg, th.attrs_of(load(folder, "tg-attrs.json")), 10) if lvl == "WARN"]
    out.append((not warn, "tg_health settings: no WARN" + ("" if not warn else f" — {warn[0]}")))
    body = (folder / "health.txt").read_text(encoding="utf-8")
    out.append(('"status": "ok"' in body, "curl http://<ALB DNS>/health returned TaskFlow's {\"status\": \"ok\"}"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--after-cleanup", action="store_true")
    a = ap.parse_args()
    try:
        if a.after_cleanup:
            left = [m["ResourceARN"] for m in load(a.folder, "after-cleanup.json").get("ResourceTagMappingList", [])]
            results = [(not left, f"no resources tagged Project=lab08 remain ({len(left)} left)")]
        else:
            results = check(a.folder)
    except (OSError, KeyError, ValueError, IndexError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
