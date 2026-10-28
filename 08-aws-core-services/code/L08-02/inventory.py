#!/usr/bin/env python3
"""inventory.py — boto3 দিয়ে read-only inventory: কোন region-এ কী চলছে (বিলের সম্ভাব্য উৎস)। কিছু বদলায় না।

  pip install boto3                         # venv-এ (L05-01)
  aws sso login --profile learn-admin
  python3 inventory.py --profile learn-admin --regions ap-south-1 us-east-1 > inventory.json
  python3 inventory.py --profile learn-admin --all-regions --summary

শুধু Describe/List call: sts:GetCallerIdentity, ec2:DescribeRegions/Instances/Volumes/Addresses/NatGateways,
elbv2:DescribeLoadBalancers, s3:ListBuckets — ReadOnlyAccess যথেষ্ট। Output-এর রূপ L08-12-এর cleanup plan-এর input।
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from typing import Any


def tags_of(item: dict[str, Any]) -> dict[str, str]:
    return {t["Key"]: t["Value"] for t in item.get("Tags", []) or []}


def arn_kind(arn: str) -> str:
    """sts get-caller-identity-র Arn → কে আমি: root, iam-user, assumed-role (SSO-ও এখানে), federated।"""
    resource = arn.split(":", 5)[-1]
    if resource == "root":
        return "root"
    if resource.startswith("user/"):
        return "iam-user"
    if resource.startswith("assumed-role/"):
        role = resource.split("/")[1]
        return "assumed-role (IAM Identity Center)" if role.startswith("AWSReservedSSO_") else "assumed-role"
    if resource.startswith("federated-user/"):
        return "federated-user"
    return "unknown"


def pages(client: Any, op: str, key: str, **kw: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for page in client.get_paginator(op).paginate(**kw):
        out.extend(page.get(key, []))
    return out


def region_inventory(session: Any, region: str) -> list[dict[str, Any]]:
    ec2 = session.client("ec2", region_name=region)
    out: list[dict[str, Any]] = []
    for res in pages(ec2, "describe_instances", "Reservations"):
        for i in res["Instances"]:
            state = i["State"]["Name"]
            if state == "terminated":
                continue
            out.append({"region": region, "type": "ec2-instance", "id": i["InstanceId"], "state": state,
                        "tags": tags_of(i), "detail": {"instance_type": i.get("InstanceType"),
                                                       "public_ip": i.get("PublicIpAddress")}})
    for v in pages(ec2, "describe_volumes", "Volumes"):
        out.append({"region": region, "type": "ebs-volume", "id": v["VolumeId"], "state": v["State"],
                    "tags": tags_of(v), "detail": {"size_gb": v.get("Size"),
                                                   "attached_to": [a["InstanceId"] for a in v.get("Attachments", [])]}})
    for addr in ec2.describe_addresses().get("Addresses", []):           # paginator নেই
        out.append({"region": region, "type": "elastic-ip", "id": addr.get("AllocationId", addr.get("PublicIp")),
                    "state": "associated" if addr.get("AssociationId") else "unassociated",
                    "tags": tags_of(addr), "detail": {"public_ip": addr.get("PublicIp")}})
    for n in pages(ec2, "describe_nat_gateways", "NatGateways"):
        if n["State"] in ("deleted", "failed"):
            continue
        out.append({"region": region, "type": "nat-gateway", "id": n["NatGatewayId"], "state": n["State"],
                    "tags": tags_of(n), "detail": {"subnet": n.get("SubnetId")}})
    elb = session.client("elbv2", region_name=region)
    for lb in pages(elb, "describe_load_balancers", "LoadBalancers"):
        out.append({"region": region, "type": "load-balancer", "id": lb["LoadBalancerArn"], "state": lb["State"]["Code"],
                    "tags": {}, "detail": {"name": lb["LoadBalancerName"], "scheme": lb.get("Scheme")}})
    return out


def collect(session: Any, regions: list[str] | None) -> dict[str, Any]:
    ident = session.client("sts").get_caller_identity()
    if regions is None:
        ec2 = session.client("ec2", region_name=session.region_name or "us-east-1")
        regions = sorted(r["RegionName"] for r in ec2.describe_regions()["Regions"])   # শুধু enabled region
    resources: list[dict[str, Any]] = []
    for region in regions:
        resources += region_inventory(session, region)
    for b in session.client("s3").list_buckets().get("Buckets", []):
        resources.append({"region": "global", "type": "s3-bucket", "id": b["Name"], "state": "exists", "tags": {},
                          "detail": {"created": str(b.get("CreationDate"))}})
    return {"account": ident["Account"], "caller": ident["Arn"], "caller_kind": arn_kind(ident["Arn"]),
            "regions": regions, "resources": resources}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Read-only AWS inventory (boto3).")
    ap.add_argument("--profile")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--regions", nargs="+")
    g.add_argument("--all-regions", action="store_true")
    ap.add_argument("--summary", action="store_true", help="counts per region/type instead of JSON")
    a = ap.parse_args(argv)
    try:
        import boto3  # শুধু আসল চালানোয় লাগে
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        print("error: boto3 is not installed — python3 -m pip install boto3 (inside a venv)", file=sys.stderr)
        return 2
    try:
        data = collect(boto3.Session(profile_name=a.profile), None if a.all_regions else a.regions)
    except (BotoCoreError, ClientError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if data["caller_kind"] == "root":
        print("warning: running as ROOT — use an admin/read-only identity (L08-01)", file=sys.stderr)
    if a.summary:
        print(f"account {data['account']} as {data['caller_kind']}")
        for (region, kind), n in sorted(Counter((r["region"], r["type"]) for r in data["resources"]).items()):
            print(f"  {region:<16} {kind:<14} {n}")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
