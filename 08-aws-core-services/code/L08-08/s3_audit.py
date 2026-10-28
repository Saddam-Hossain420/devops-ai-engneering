#!/usr/bin/env python3
"""s3_audit.py — S3 bucket-এর public exposure, TLS, versioning, lifecycle ও ownership যাচাই (offline, শুধু পড়ে)।

প্রতিটি bucket-এর জন্য একটি folder, যাতে `aws s3api` output (না থাকলে = configure করা হয়নি):
  B=my-bucket; mkdir -p s3/$B
  aws s3api get-public-access-block   --bucket $B > s3/$B/public-access-block.json
  aws s3api get-bucket-policy         --bucket $B > s3/$B/policy.json
  aws s3api get-bucket-versioning     --bucket $B > s3/$B/versioning.json
  aws s3api get-bucket-lifecycle-configuration --bucket $B > s3/$B/lifecycle.json
  aws s3api get-bucket-ownership-controls      --bucket $B > s3/$B/ownership.json
  (`NoSuch…` error হলে খালি file তৈরি হয় — tool খালি file-কে "নেই" ধরে)
  python3 s3_audit.py s3/*/

Exit: 0 কোনো CRITICAL নেই, 1 আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PAB_KEYS = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")
# এই condition key-গুলো থাকলে Principal "*"-এর statement আর "সবার জন্য" নয়
LIMITING_KEYS = {"aws:sourcevpce", "aws:sourcevpc", "aws:sourceip", "aws:principalorgid", "aws:principalaccount",
                 "aws:sourcearn", "aws:sourceaccount", "aws:userid", "aws:principalarn"}


def load(folder: Path, name: str) -> dict[str, Any] | None:
    p = folder / f"{name}.json"
    if not p.is_file() or not p.read_text(encoding="utf-8").strip():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else [x]


def is_public_principal(p: Any) -> bool:
    return p == "*" or (isinstance(p, dict) and "*" in as_list(p.get("AWS", [])))


def cond_keys(stmt: dict[str, Any]) -> set[str]:
    return {k.lower() for pairs in (stmt.get("Condition") or {}).values() for k in pairs}


def audit_bucket(folder: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pab = (load(folder, "public-access-block") or {}).get("PublicAccessBlockConfiguration")
    off = [k for k in PAB_KEYS if not (pab or {}).get(k)]
    policy_doc = load(folder, "policy")
    policy = json.loads(policy_doc["Policy"]) if policy_doc else {"Statement": []}
    public_stmts = [s for s in as_list(policy.get("Statement", [])) if s.get("Effect") == "Allow"
                    and is_public_principal(s.get("Principal")) and not (cond_keys(s) & LIMITING_KEYS)]
    for s in public_stmts:
        acts = ", ".join(as_list(s.get("Action", [])))
        level = "CRITICAL" if not (pab or {}).get("RestrictPublicBuckets") else "WARN"
        note = "" if level == "CRITICAL" else " (blocked today by RestrictPublicBuckets — remove it anyway)"
        out.append((level, f"policy {s.get('Sid', '?')} allows {acts} to everyone{note}"))
    if off:
        out.append(("WARN" if not public_stmts else "CRITICAL",
                    "block public access off: " + ", ".join(off) + " — turn all four on unless this is a deliberate "
                    "public website (prefer CloudFront + OAC)"))
    tls = any(s.get("Effect") == "Deny" and "aws:securetransport" in cond_keys(s)
              for s in as_list(policy.get("Statement", [])))
    if not tls:
        out.append(("WARN", "no Deny for aws:SecureTransport=false — plain HTTP requests are allowed"))
    status = (load(folder, "versioning") or {}).get("Status")
    rules = [r for r in (load(folder, "lifecycle") or {}).get("Rules", []) if r.get("Status") == "Enabled"]
    if status != "Enabled":
        out.append(("WARN", f"versioning {status or 'never enabled'} — an overwrite or delete cannot be undone"))
    elif not any("NoncurrentVersionExpiration" in r for r in rules):
        out.append(("WARN", "versioning on but no NoncurrentVersionExpiration — old versions accumulate (and are billed)"))
    if not any("AbortIncompleteMultipartUpload" in r for r in rules):
        out.append(("INFO", "no AbortIncompleteMultipartUpload rule — failed uploads' parts stay billed"))
    own = (load(folder, "ownership") or {}).get("OwnershipControls", {}).get("Rules", [{}])
    if own[0].get("ObjectOwnership") != "BucketOwnerEnforced":
        out.append(("WARN", f"object ownership {own[0].get('ObjectOwnership', 'not set')} — ACLs active; "
                            "BucketOwnerEnforced disables them"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Audit S3 buckets from saved s3api output (offline).")
    ap.add_argument("folders", nargs="+", type=Path)
    a = ap.parse_args(argv)
    crit = 0
    try:
        for folder in a.folders:
            if not folder.is_dir():
                continue
            findings = audit_bucket(folder)
            order = {"CRITICAL": 0, "WARN": 1, "INFO": 2}
            print(f"{folder.name}: " + ("ok" if not findings else f"{len(findings)} finding(s)"))
            for lvl, msg in sorted(findings, key=lambda f: order[f[0]]):
                print(f"  {lvl:<8}  {msg}")
            crit += sum(lvl == "CRITICAL" for lvl, _ in findings)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1 if crit else 0


if __name__ == "__main__":
    raise SystemExit(main())
