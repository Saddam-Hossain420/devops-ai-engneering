#!/usr/bin/env python3
"""ec2_audit.py — `aws ec2 describe-instances` output থেকে EC2-এর নিরাপত্তা ও খরচের ঝুঁকি (offline, শুধু পড়ে)।

  aws ec2 describe-instances > instances.json        # filter নয় — tag-হীনগুলোও দেখতে হবে
  python3 ec2_audit.py instances.json --required-tags Project,Owner

খোঁজে: IMDSv1 চালু (HttpTokens=optional) · public IPv4 · instance profile নেই · প্রয়োজনীয় tag নেই ·
DeleteOnTermination=false (terminate-এর পরে disk রয়ে যায়, বিল চলে) · stopped (EBS-এর বিল চলছে) ·
পুরোনো প্রজন্মের type (t2/m4/c4/r4) · container-এর জন্য hop limit।
Exit: 0 কোনো CRITICAL নেই, 1 আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

OLD_FAMILIES = ("t2.", "m4.", "c4.", "r4.", "m3.", "c3.", "r3.", "t1.", "m1.")


def instances_of(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for r in doc.get("Reservations", []) for i in r.get("Instances", [])]


def tags_of(i: dict[str, Any]) -> dict[str, str]:
    return {t["Key"]: t["Value"] for t in i.get("Tags", []) or []}


def audit(instances: list[dict[str, Any]], required: list[str]) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for i in instances:
        iid, state = i["InstanceId"], i["State"]["Name"]
        if state in ("terminated", "shutting-down"):
            continue
        md = i.get("MetadataOptions", {})
        if md.get("HttpEndpoint", "enabled") == "enabled" and md.get("HttpTokens") != "required":
            if i.get("IamInstanceProfile"):
                out.append(("CRITICAL", iid, "IMDSv1 allowed (HttpTokens=optional) — an SSRF bug can read the role's "
                                             "credentials; modify-instance-metadata-options --http-tokens required"))
            else:
                out.append(("WARN", iid, "IMDSv1 allowed (HttpTokens=optional) — no role yet, but require IMDSv2 "
                                         "before one is attached"))
        if md.get("HttpPutResponseHopLimit", 1) > 1:
            out.append(("INFO", iid, f"metadata hop limit {md['HttpPutResponseHopLimit']} — needed only if containers "
                                     "on the host must reach IMDS"))
        if i.get("PublicIpAddress"):
            out.append(("WARN", iid, f"public IPv4 {i['PublicIpAddress']} — billed, and reachable if a security group "
                                     "allows it; behind a load balancer use private only"))
        if not i.get("IamInstanceProfile"):
            out.append(("WARN", iid, "no instance profile — the app will need keys on disk, or cannot call AWS"))
        missing = [t for t in required if not tags_of(i).get(t)]
        if missing:
            out.append(("WARN", iid, "missing tags: " + ", ".join(missing) + " — cleanup and cost reports cannot find it"))
        for bdm in i.get("BlockDeviceMappings", []):
            ebs = bdm.get("Ebs", {})
            if ebs and ebs.get("DeleteOnTermination") is False:
                root = " (root)" if bdm.get("DeviceName") == i.get("RootDeviceName") else ""
                out.append(("WARN", iid, f"{ebs.get('VolumeId')}{root} DeleteOnTermination=false — survives terminate "
                                         "and keeps billing; intended?"))
        if state == "stopped":
            vols = [b["Ebs"]["VolumeId"] for b in i.get("BlockDeviceMappings", []) if b.get("Ebs")]
            out.append(("INFO", iid, f"stopped — no compute charge, but volumes {', '.join(vols)} are still billed"))
        if i.get("InstanceType", "").startswith(OLD_FAMILIES):
            out.append(("INFO", iid, f"{i['InstanceType']} is a previous generation — compare a current one's "
                                     "price/performance on the pricing page"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Audit EC2 instances from describe-instances output (offline).")
    ap.add_argument("file", type=Path)
    ap.add_argument("--required-tags", default="Project,Owner")
    a = ap.parse_args(argv)
    try:
        instances = instances_of(json.loads(a.file.read_text(encoding="utf-8")))
        findings = audit(instances, [t.strip() for t in a.required_tags.split(",") if t.strip()])
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    order = {"CRITICAL": 0, "WARN": 1, "INFO": 2}
    for lvl, iid, msg in sorted(findings, key=lambda f: (order[f[0]], f[1])):
        print(f"{lvl:<8}  {iid:<14} {msg}")
    crit = sum(f[0] == "CRITICAL" for f in findings)
    print(f"{len(instances)} instance(s): {crit} critical, {sum(f[0] == 'WARN' for f in findings)} warning(s)")
    return 1 if crit else 0


if __name__ == "__main__":
    raise SystemExit(main())
