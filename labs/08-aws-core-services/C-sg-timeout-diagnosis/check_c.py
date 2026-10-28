#!/usr/bin/env python3
"""Lab 08-C verification — "ALB-এর সব target Target.Timeout" incident-এর fix ও diagnosis যাচাই (সম্পূর্ণ offline)।

  python3 check_c.py broken                                    # ভাঙা অবস্থা — কোন check কেন FAIL
  python3 check_c.py ~/lab08c --diagnosis ~/lab08c/diagnosis.md

~/lab08c-এ শুধু আপনার ঠিক করা `security-groups.json` ও `network-acls.json`; বাকি file `broken/` থেকে নেওয়া হয়।
Fix হতে হবে **ন্যূনতম**: app security group internet-এর জন্য খোলা নয়, app subnet-এর NACL SSH আটকে রাখে,
এবং NACL-এর ফেরত পথ শুধু VPC-র ভেতরে (internet-এর ephemeral port-এ নয়)।
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "08-aws-core-services" / "code" / "L08-05"))
import sg_reach as sr  # noqa: E402

BROKEN = HERE / "broken"
INTERNET = "198.51.100.7"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check(folder: Path, diagnosis: str | None) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    pick = lambda name: folder / name if (folder / name).is_file() else BROKEN / name   # noqa: E731
    groups = {g["GroupId"]: g for g in load(pick("security-groups.json"))["SecurityGroups"]}
    acls = load(pick("network-acls.json"))["NetworkAcls"]
    subnets = {s["SubnetId"]: s for s in load(BROKEN / "subnets.json")["Subnets"]}
    lb = load(BROKEN / "load-balancers.json")["LoadBalancers"][0]
    instances = [i for r in load(BROKEN / "instances.json")["Reservations"] for i in r["Instances"]]
    alb_sgs, lb_subnets = lb["SecurityGroups"], [z["SubnetId"] for z in lb["AvailabilityZones"]]

    def rep(subnet: str) -> str:
        return str(ipaddress.ip_network(subnets[subnet]["CidrBlock"])[10])

    for i in instances:
        app_sgs = [g["GroupId"] for g in i["SecurityGroups"]]
        for s in lb_subnets:
            steps = sr.check(sr.Flow("alb→app", rep(s), i["PrivateIpAddress"], 8000, src_sgs=alb_sgs, src_subnet=s,
                                     dst_sgs=app_sgs, dst_subnet=i["SubnetId"]), groups, acls)
            ok = all(o for o, _ in steps)
            out.append((ok, f"ALB ({s}) → {i['InstanceId']}:8000" + ("" if ok else f" — dropped at: {steps[-1][1]}")))
        for port in (8000, 22):
            steps = sr.check(sr.Flow("inet→app", INTERNET, i["PrivateIpAddress"], port, dst_sgs=app_sgs,
                                     dst_subnet=i["SubnetId"]), groups, acls)
            out.append((not all(o for o, _ in steps), f"internet → {i['InstanceId']}:{port} stays blocked"))
    steps = sr.check(sr.Flow("inet→alb", INTERNET, rep(lb_subnets[0]), 80, dst_sgs=alb_sgs, dst_subnet=lb_subnets[0]),
                     groups, acls)
    out.append((all(o for o, _ in steps), "internet → ALB:80 still allowed"))

    audit = sr.audit(groups)
    stale = [m for _, _, m in audit if "not in this input" in m]
    out.append((not [m for lvl, _, m in audit if lvl == "CRITICAL"], "security group audit: no CRITICAL"))
    out.append((not stale, "no reference to a security group that does not exist" + ("" if not stale else f" — {stale[0]}")))
    app_sg = groups[instances[0]["SecurityGroups"][0]["GroupId"]]
    world = [r for r in app_sg.get("IpPermissions", []) if any(x["CidrIp"] == "0.0.0.0/0" for x in r.get("IpRanges", []))]
    out.append((not world, "app security group not opened to 0.0.0.0/0 (that would be a 'fix' that hides the cause)"))

    app_acl = sr.acl_for(acls, instances[0]["SubnetId"])
    out.append((not sr.acl_decides(app_acl, False, INTERNET, 22, "tcp")[0], f"{app_acl['NetworkAclId']}: SSH from internet still denied"))
    out.append((sr.acl_decides(app_acl, True, rep(lb_subnets[0]), 50000, "tcp")[0],
                f"{app_acl['NetworkAclId']}: replies to the ALB's ephemeral ports allowed"))
    out.append((not sr.acl_decides(app_acl, True, INTERNET, 50000, "tcp")[0],
                f"{app_acl['NetworkAclId']}: replies limited to the VPC (not every internet ephemeral port)"))

    if diagnosis is not None:
        text = diagnosis.lower()
        out.append(("sg-alb-old" in text, "diagnosis names the stale security group reference (sg-alb-old)"))
        out.append((bool(re.search(r"ephemeral|1024", text)), "diagnosis explains the ephemeral-port return path"))
        out.append(("acl-app-hardened" in text, "diagnosis names the network ACL (acl-app-hardened)"))
        out.append(("refused" in text, "diagnosis explains why the symptom is a timeout, not 'connection refused'"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="'broken' or your folder with fixed security-groups.json/network-acls.json")
    ap.add_argument("--diagnosis", type=Path)
    a = ap.parse_args()
    folder = BROKEN if str(a.folder) == "broken" else a.folder
    try:
        diagnosis = a.diagnosis.read_text(encoding="utf-8") if a.diagnosis else None
        results = check(folder, diagnosis)
    except (OSError, KeyError, ValueError, IndexError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    if diagnosis is None and folder != BROKEN:
        print("note: --diagnosis not given — diagnosis.md not checked")
    print("ALL CHECKS PASSED" if not failed and diagnosis is not None else f"{failed} CHECK(S) FAILED")
    return 0 if not failed and diagnosis is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
