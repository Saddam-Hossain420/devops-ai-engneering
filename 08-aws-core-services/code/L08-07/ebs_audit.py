#!/usr/bin/env python3
"""ebs_audit.py — EBS volume ও snapshot-এর খরচ ও নিরাপত্তার ঝুঁকি, AWS CLI output থেকে (offline, শুধু পড়ে)।

  aws ec2 describe-volumes > volumes.json
  aws ec2 describe-snapshots --owner-ids self > snapshots.json
  aws ec2 get-ebs-encryption-by-default > encryption-default.json          # ঐচ্ছিক
  python3 ebs_audit.py volumes.json snapshots.json --encryption-default encryption-default.json --today 2026-10-28

খোঁজে: কোথাও attached নয় (available) · encrypted নয় · gp2 (gp3 বিবেচনা) · DeleteOnTermination=false ·
Project tag নেই · যে volume থেকে নেওয়া সেটা আর নেই এমন পুরোনো snapshot · encrypt-না-করা snapshot ·
account-এ default encryption বন্ধ। কিছু মোছে না — মোছার আগে মালিক, AMI ব্যবহার ও retention নিয়ম দেখুন।
Exit: 0 কোনো CRITICAL নেই, 1 আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


def day(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def tags_of(item: dict[str, Any]) -> dict[str, str]:
    return {t["Key"]: t["Value"] for t in item.get("Tags", []) or []}


def audit(volumes: list[dict[str, Any]], snapshots: list[dict[str, Any]], today: date, old_days: int,
          encryption_default: bool | None) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    if encryption_default is False:
        out.append(("WARN", "account", "EBS encryption by default is off in this region — "
                                       "aws ec2 enable-ebs-encryption-by-default"))
    existing = {v["VolumeId"] for v in volumes}
    for v in volumes:
        vid, size = v["VolumeId"], v.get("Size", "?")
        if v.get("State") == "available":
            age = (today - day(v["CreateTime"])).days if v.get("CreateTime") else "?"
            out.append(("WARN", vid, f"{size} GiB not attached to anything (created {age} days ago) — billed; "
                                     "snapshot if needed, then delete"))
        if not v.get("Encrypted"):
            out.append(("CRITICAL", vid, f"{size} GiB not encrypted — data at rest unprotected; "
                                         "snapshot → copy with --encrypted → new volume"))
        if v.get("VolumeType") == "gp2":
            out.append(("INFO", vid, "gp2 — gp3 decouples IOPS/throughput from size and is often cheaper per GiB; "
                                     "modify-volume --volume-type gp3 works online (check pricing)"))
        for att in v.get("Attachments", []):
            if att.get("DeleteOnTermination") is False:
                out.append(("INFO", vid, f"DeleteOnTermination=false on {att.get('InstanceId')} — survives terminate"))
        if not tags_of(v).get("Project"):
            out.append(("WARN", vid, "no Project tag — cleanup and cost reports cannot attribute it"))
    for s in snapshots:
        sid = s["SnapshotId"]
        age = (today - day(s["StartTime"])).days
        from_ami = "CreateImage" in s.get("Description", "")
        if not s.get("Encrypted"):
            out.append(("WARN", sid, "snapshot not encrypted — and it could be shared publicly by mistake"))
        if age > old_days and s.get("VolumeId") not in existing and not from_ami:
            out.append(("WARN", sid, f"{age} days old, source volume {s.get('VolumeId')} no longer exists — "
                                     f"{s.get('VolumeSize', '?')} GiB billed (incremental); still needed?"))
        elif from_ami and age > old_days:
            out.append(("INFO", sid, f"{age} days old, backs an AMI — deregister the AMI first if it is unused"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Audit EBS volumes and snapshots (offline).")
    ap.add_argument("volumes", type=Path)
    ap.add_argument("snapshots", type=Path, nargs="?")
    ap.add_argument("--encryption-default", type=Path)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--old-days", type=int, default=90)
    a = ap.parse_args(argv)
    try:
        volumes = json.loads(a.volumes.read_text(encoding="utf-8"))["Volumes"]
        snapshots = json.loads(a.snapshots.read_text(encoding="utf-8"))["Snapshots"] if a.snapshots else []
        enc = (json.loads(a.encryption_default.read_text(encoding="utf-8"))["EbsEncryptionByDefault"]
               if a.encryption_default else None)
        findings = audit(volumes, snapshots, a.today, a.old_days, enc)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    order = {"CRITICAL": 0, "WARN": 1, "INFO": 2}
    for lvl, rid, msg in sorted(findings, key=lambda f: (order[f[0]], f[1])):
        print(f"{lvl:<8}  {rid:<20} {msg}")
    gib = sum(v.get("Size", 0) for v in volumes if v.get("State") == "available")
    crit = sum(f[0] == "CRITICAL" for f in findings)
    print(f"{len(volumes)} volume(s), {len(snapshots)} snapshot(s): {crit} critical; "
          f"{gib} GiB in unattached volumes")
    return 1 if crit else 0


if __name__ == "__main__":
    raise SystemExit(main())
