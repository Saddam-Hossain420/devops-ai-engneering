#!/usr/bin/env python3
"""r53_plan.py — Route 53-এর বর্তমান record ও কাঙ্ক্ষিত record মিলিয়ে নিরাপদ change batch বানায় (offline, কিছু পাঠায় না)।

  aws route53 list-resource-record-sets --hosted-zone-id Z0123 > current.json
  python3 r53_plan.py current.json desired.json --zone example.com --out changes.json
  aws route53 change-resource-record-sets --hosted-zone-id Z0123 --change-batch file://changes.json

desired.json: [{"name": "app", "type": "A", "alias": {"dns": "lab08-alb-1.ap-south-1.elb.amazonaws.com",
                 "zone": "<ALB-এর CanonicalHostedZoneId>", "evaluate_health": true}},
                {"name": "www", "type": "CNAME", "ttl": 300, "values": ["app.example.com"]}]
নাম zone-এর সাপেক্ষে ("@" = apex) বা পূর্ণ। শুধু desired-এ থাকা নামগুলো পরিচালিত হয়; --prune দিলে desired-এ নেই এমন
(NS/SOA ছাড়া) record DELETE হয়। Validation: apex-এ CNAME নয় · CNAME-এর সাথে একই নামে অন্য record নয় · alias-এ TTL নয় ·
TTL সীমা · বর্তমান TTL বড় হলে আগে TTL কমানোর সতর্কতা (L06-01)।
Exit: 0 plan লেখা হয়েছে (বা কোনো পরিবর্তন নেই), 1 validation error, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

OCTAL = re.compile(r"\\(\d{3})")


def fqdn(name: str, zone: str) -> str:
    zone = zone.rstrip(".").lower() + "."
    name = OCTAL.sub(lambda m: chr(int(m.group(1), 8)), name.strip()).lower()   # Route 53: '*' আসে '\052' হিসেবে
    if name in ("@", "", zone, zone.rstrip(".")):
        return zone
    if name.endswith("."):
        return name
    return name + "." + zone if not name.endswith(zone.rstrip(".")) else name + "."


def normalize_current(doc: dict[str, Any], zone: str) -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for r in doc.get("ResourceRecordSets", []):
        rec = dict(r)
        rec["Name"] = fqdn(r["Name"], zone)
        out[(rec["Name"], r["Type"])] = rec
    return out


def desired_to_rrset(d: dict[str, Any], zone: str) -> dict[str, Any]:
    rr: dict[str, Any] = {"Name": fqdn(d["name"], zone), "Type": d["type"].upper()}
    if "alias" in d:
        a = d["alias"]
        rr["AliasTarget"] = {"HostedZoneId": a["zone"], "DNSName": a["dns"].rstrip(".") + ".",
                             "EvaluateTargetHealth": bool(a.get("evaluate_health", False))}
    else:
        rr["TTL"] = int(d.get("ttl", 300))
        rr["ResourceRecords"] = [{"Value": v} for v in d["values"]]
    return rr


def validate(desired: list[dict[str, Any]], current: dict[tuple[str, str], dict[str, Any]], zone: str,
             prune: bool = False) -> list[str]:
    errors = []
    apex = fqdn("@", zone)
    names: dict[str, set[str]] = {}
    for d in desired:
        name, typ = fqdn(d["name"], zone), d["type"].upper()
        names.setdefault(name, set()).add(typ)
        if typ in ("NS", "SOA") and name == apex:
            errors.append(f"{name} {typ}: apex NS/SOA are managed by Route 53 — do not change them here")
        if "alias" in d and "ttl" in d:
            errors.append(f"{name} {typ}: alias records have no TTL (Route 53 uses the target's)")
        if "alias" not in d and not d.get("values"):
            errors.append(f"{name} {typ}: needs 'values' or 'alias'")
        if "ttl" in d and not 0 <= int(d["ttl"]) <= 2147483647:
            errors.append(f"{name} {typ}: TTL out of range")
        if typ == "CNAME" and name == apex:
            errors.append(f"{name} CNAME: not allowed at the zone apex (RFC 1034) — use an alias A/AAAA record")
    for name, types in names.items():
        # --prune না দিলে বর্তমান record-গুলো থেকে যায় — সেগুলোও গুনতে হবে
        kept = set() if prune else {t for (n, t) in current if n == name and t not in ("NS", "SOA")}
        together = types | kept
        if "CNAME" in together and len(together) > 1:
            errors.append(f"{name}: CNAME cannot coexist with {sorted(together - {'CNAME'})}"
                          + ("" if prune else " — remove the old record first, or use --prune"))
    return errors


def same(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = ("TTL", "ResourceRecords", "AliasTarget")
    norm = [{k: (json.dumps(x.get(k), sort_keys=True).lower() if k == "AliasTarget" else x.get(k)) for k in keys}
            for x in (a, b)]
    return norm[0] == norm[1]


def plan(current_doc: dict[str, Any], desired: list[dict[str, Any]], zone: str, prune: bool,
         ttl_warn: int = 3600) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    current = normalize_current(current_doc, zone)
    errors = validate(desired, current, zone, prune)
    changes: list[dict[str, Any]] = []
    notes: list[str] = []
    wanted = {}
    for d in desired:
        rr = desired_to_rrset(d, zone)
        wanted[(rr["Name"], rr["Type"])] = rr
    for key, rr in wanted.items():
        old = current.get(key)
        if old and same(old, rr):
            continue
        changes.append({"Action": "UPSERT", "ResourceRecordSet": rr})
        if old and old.get("TTL", 0) > ttl_warn:
            notes.append(f"{key[0]} {key[1]}: current TTL {old['TTL']}s — resolvers may serve the old value that long; "
                         f"lower the TTL first and wait {old['TTL']}s before this change")
    if prune:
        deletes = [{"Action": "DELETE", "ResourceRecordSet": old} for key, old in current.items()
                   if key not in wanted and not (key[1] in ("NS", "SOA") and key[0] == fqdn("@", zone))]
        changes = deletes + changes                     # CNAME → A-র মতো বদলে DELETE আগে লাগে
    return changes, errors, notes


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Plan Route 53 record changes (offline).")
    ap.add_argument("current", type=Path, help="list-resource-record-sets output")
    ap.add_argument("desired", type=Path)
    ap.add_argument("--zone", required=True)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--prune", action="store_true")
    a = ap.parse_args(argv)
    try:
        changes, errors, notes = plan(json.loads(a.current.read_text(encoding="utf-8")),
                                      json.loads(a.desired.read_text(encoding="utf-8")), a.zone, a.prune)
    except (OSError, KeyError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for e in errors:
        print(f"ERROR  {e}")
    if errors:
        return 1
    for n in notes:
        print(f"WARN   {n}")
    for c in changes:
        rr = c["ResourceRecordSet"]
        target = rr["AliasTarget"]["DNSName"] if "AliasTarget" in rr else ", ".join(v["Value"] for v in rr["ResourceRecords"])
        print(f"{c['Action']:<6} {rr['Name']:<28} {rr['Type']:<5} {('alias' if 'AliasTarget' in rr else rr['TTL']):<6} {target}")
    if not changes:
        print("no changes")
        return 0
    batch = {"Comment": "planned by r53_plan.py", "Changes": changes}
    if a.out:
        a.out.write_text(json.dumps(batch, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {a.out} — review, then: aws route53 change-resource-record-sets --hosted-zone-id <ID> "
              f"--change-batch file://{a.out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
