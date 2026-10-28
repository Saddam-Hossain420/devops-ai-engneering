#!/usr/bin/env python3
"""cleanup_plan.py — একটি tag-এর সব resource মোছার bash script বানায়, নির্ভরতার সঠিক ক্রমে। নিজে কিছু মোছে না।

  aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=lab08 > tagged.json
  python3 cleanup_plan.py tagged.json --tag Project=lab08 --account 111122223333 --region ap-south-1 > cleanup.sh
  bash cleanup.sh                 # DRY RUN: শুধু command দেখায়
  EXECUTE=yes bash cleanup.sh     # আসলে মোছে — account ও region মিললে তবেই

ক্রম: load balancer → target group → instance → NAT gateway → Elastic IP → volume → snapshot → security group →
internet gateway → subnet → route table → VPC → S3 bucket (সব version সহ) → alarm → SNS → log group।
যে type-এর নিয়ম নেই (IAM role/instance profile, Route 53 zone, SSM parameter …) সেগুলো stderr-এ "manual" তালিকায় —
হাতে মুছুন (L08-03, L08-10); IAM-এর মতো কিছু resource tagging API-র তালিকায় না-ও আসতে পারে।
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_VALUES = re.compile(r"(?i)^(prod|production|live|main|shared|default)$")
ORDER = ["loadbalancer", "targetgroup", "instance", "natgateway", "elastic-ip", "volume", "snapshot",
         "security-group", "internet-gateway", "subnet", "route-table", "vpc", "bucket", "alarm", "topic", "log-group"]


@dataclass
class Res:
    arn: str
    kind: str
    id: str


def parse_arn(arn: str) -> Res:
    parts = arn.split(":", 5)
    if len(parts) < 6 or parts[0] != "arn":
        raise ValueError(f"not an ARN: {arn}")
    service, resource = parts[2], parts[5]
    if service == "ec2":
        kind, _, rid = resource.partition("/")
        return Res(arn, kind, rid)
    if service == "elasticloadbalancing":
        kind = resource.split("/", 1)[0]
        return Res(arn, kind, arn)                                     # ELB API ARN নেয়
    if service == "s3":
        return Res(arn, "bucket", resource)
    if service == "cloudwatch" and resource.startswith("alarm:"):
        return Res(arn, "alarm", resource[len("alarm:"):])
    if service == "sns":
        return Res(arn, "topic", arn)
    if service == "logs" and resource.startswith("log-group:"):
        return Res(arn, "log-group", resource[len("log-group:"):].removesuffix(":*"))
    return Res(arn, f"{service}:{resource.split('/')[0].split(':')[0]}", resource)


def commands(r: Res) -> list[str]:
    q = f'"{r.id}"'
    c = {
        "loadbalancer": [f"run aws elbv2 delete-load-balancer --load-balancer-arn {q}",
                         f"run aws elbv2 wait load-balancers-deleted --load-balancer-arns {q}"],
        "targetgroup": [f"run aws elbv2 delete-target-group --target-group-arn {q}"],
        "instance": [f"run aws ec2 terminate-instances --instance-ids {q}",
                     f"run aws ec2 wait instance-terminated --instance-ids {q}"],
        "natgateway": [f"run aws ec2 delete-nat-gateway --nat-gateway-id {q}",
                       f"run aws ec2 wait nat-gateway-deleted --nat-gateway-ids {q}"],
        "elastic-ip": [f"run aws ec2 release-address --allocation-id {q}"],
        # root volume (DeleteOnTermination) instance-এর সাথেই মুছে যায় — নইলে NotFound-এ set -e পুরো script থামাত
        "volume": [f"if aws ec2 describe-volumes --volume-ids {q} >/dev/null 2>&1; then "
                   f"run aws ec2 delete-volume --volume-id {q}; "
                   f'else echo "skip {r.id}: not found (deleted with its instance)"; fi'],
        "snapshot": [f"run aws ec2 delete-snapshot --snapshot-id {q}"],
        "security-group": [f"revoke_sg_refs {q}", f"retry aws ec2 delete-security-group --group-id {q}"],
        "internet-gateway": [f"VPC_OF_IGW=$(aws ec2 describe-internet-gateways --internet-gateway-ids {q} "
                             "--query 'InternetGateways[0].Attachments[0].VpcId' --output text)",
                             f'[ "$VPC_OF_IGW" = "None" ] || run aws ec2 detach-internet-gateway '
                             f'--internet-gateway-id {q} --vpc-id "$VPC_OF_IGW"',
                             f"run aws ec2 delete-internet-gateway --internet-gateway-id {q}"],
        "subnet": [f"retry aws ec2 delete-subnet --subnet-id {q}"],
        "route-table": [f"MAIN=$(aws ec2 describe-route-tables --route-table-ids {q} "
                        "--query 'RouteTables[0].Associations[?Main]|length(@)' --output text)",
                        f'[ "$MAIN" != "0" ] && echo "skip {r.id}: main route table (deleted with the VPC)" '
                        f"|| run aws ec2 delete-route-table --route-table-id {q}"],
        "vpc": [f"retry aws ec2 delete-vpc --vpc-id {q}"],
        "bucket": [f"empty_bucket {q}", f"run aws s3api delete-bucket --bucket {q}"],
        "alarm": [f"run aws cloudwatch delete-alarms --alarm-names {q}"],
        "topic": [f"run aws sns delete-topic --topic-arn {q}"],
        "log-group": [f"run aws logs delete-log-group --log-group-name {q}"],
    }
    return c.get(r.kind, [])


PRELUDE = """#!/usr/bin/env bash
# generated by cleanup_plan.py — deletes everything tagged {tag} in account {account}, region {region}
# DRY RUN unless EXECUTE=yes. Review every line before executing.
set -euo pipefail
export AWS_REGION={region}
ACTUAL=$(aws sts get-caller-identity --query Account --output text)
if [ "$ACTUAL" != "{account}" ]; then echo "refusing: credentials are for account $ACTUAL, plan is for {account}" >&2; exit 2; fi
run() {{ if [ "${{EXECUTE:-}}" = "yes" ]; then echo "+ $*"; "$@"; else echo "DRY-RUN: $*"; fi; }}
# ALB/NAT মোছার পরে তাদের network interface কয়েক মিনিট থাকে — DependencyViolation-এ অপেক্ষা করে আবার চেষ্টা
retry() {{
  if [ "${{EXECUTE:-}}" != "yes" ]; then echo "DRY-RUN: $*"; return; fi
  for i in $(seq 1 12); do echo "+ $* (try $i)"; "$@" && return; sleep 15; done
  echo "giving up: $*" >&2; return 1
}}
# security group একে অপরকে reference করলে মোছা যায় না — আগে সেই rule-গুলো revoke
revoke_sg_refs() {{
  for dir in ingress egress; do
    if [ "$dir" = ingress ]; then filt='!IsEgress'; else filt='IsEgress'; fi
    ids=$(aws ec2 describe-security-group-rules --filters Name=group-id,Values="$1"       --query "SecurityGroupRules[?ReferencedGroupInfo && $filt].SecurityGroupRuleId" --output text)
    [ -z "$ids" ] || [ "$ids" = "None" ] || run aws ec2 revoke-security-group-$dir --group-id "$1" --security-group-rule-ids $ids
  done
}}
empty_bucket() {{
  for kind in Versions DeleteMarkers; do
    while :; do
      batch=$(aws s3api list-object-versions --bucket "$1" --max-items 1000 \\
        --query "{{Objects: $kind[].{{Key:Key,VersionId:VersionId}}, Quiet: \\`true\\`}}" --output json)
      echo "$batch" | grep -q '"Key"' || break
      if [ "${{EXECUTE:-}}" = "yes" ]; then aws s3api delete-objects --bucket "$1" --delete "$batch" >/dev/null
      else echo "DRY-RUN: delete $kind in $1"; break; fi
    done
  done
}}
"""


def build(doc: dict, tag: str, account: str, region: str) -> tuple[str, list[str]]:
    key, _, value = tag.partition("=")
    if not key or not value:
        raise ValueError("--tag must be KEY=VALUE")
    if FORBIDDEN_VALUES.match(value):
        raise ValueError(f"refusing to plan deletion for tag value '{value}' — looks like a non-lab environment")
    if not re.fullmatch(r"\d{12}", account):
        raise ValueError("--account must be a 12-digit account id")
    resources = []
    for m in doc.get("ResourceTagMappingList", []):
        tags = {t["Key"]: t["Value"] for t in m.get("Tags", [])}
        if tags.get(key) != value:
            raise ValueError(f"{m['ResourceARN']} does not carry {tag} — wrong input file?")
        arn_parts = m["ResourceARN"].split(":")
        if arn_parts[3] not in ("", region) or arn_parts[4] not in ("", account):
            raise ValueError(f"{m['ResourceARN']} is outside account {account} / region {region}")
        resources.append(parse_arn(m["ResourceARN"]))
    known = sorted((r for r in resources if r.kind in ORDER), key=lambda r: ORDER.index(r.kind))
    manual = [r.arn for r in resources if r.kind not in ORDER]
    lines = [PRELUDE.format(tag=tag, account=account, region=region)]
    for kind in ORDER:
        group = [r for r in known if r.kind == kind]
        if group:
            lines.append(f"# --- {kind} ({len(group)})")
            cmds = [c for r in group for c in commands(r)]
            # SG: আগে সবগুলোর পারস্পরিক reference revoke, তারপর মোছা — নইলে একে অপরকে আটকায়
            lines += sorted(cmds, key=lambda c: not c.startswith("revoke_sg_refs")) if kind == "security-group" else cmds
    lines.append('echo "done. Not handled here: IAM role/instance profile (L08-03), '
                 'Route 53 hosted zone (L08-10) — check by hand. Re-run: python3 inventory.py --all-regions --summary"')
    return "\n".join(lines) + "\n", manual


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Write a dependency-ordered, dry-run-by-default cleanup script.")
    ap.add_argument("tagged", type=Path, help="output of resourcegroupstaggingapi get-resources")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--account", required=True)
    ap.add_argument("--region", required=True)
    a = ap.parse_args(argv)
    try:
        script, manual = build(json.loads(a.tagged.read_text(encoding="utf-8")), a.tag, a.account, a.region)
    except (OSError, KeyError, ValueError, IndexError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(script)
    for arn in manual:
        print(f"manual: {arn} (no automatic rule)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
