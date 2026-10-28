#!/usr/bin/env python3
"""Lab 08-A verification — আপনার bucket-এর setting, app role-এর policy, presigned URL-এর পরীক্ষা ও cleanup (offline)।

  python3 check_a.py ~/lab08a --bucket lab08-uploads-111122223333
  python3 check_a.py ~/lab08a --bucket lab08-uploads-111122223333 --after-cleanup

Folder-এ (README-র command দিয়ে তৈরি):
  s3/<bucket>/*.json          — s3api get-* output (L08-08)
  bucket-tagging.json         — s3api get-bucket-tagging
  app-policy.json             — TaskFlow role-এর permission policy (আপনার লেখা)
  presign-results.txt         — "before: <code>" ও "after: <code>" দুই লাইন
  after-cleanup.json          — (--after-cleanup) resourcegroupstaggingapi get-resources, Project=lab08
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for sub in ("08-aws-core-services/code/L08-08", "07-cloud-fundamentals/code/L07-05"):
    sys.path.insert(0, str(REPO / sub))
import policy_eval as pe  # noqa: E402
import policy_lint as pl  # noqa: E402
import s3_audit as sa  # noqa: E402


def requests(bucket: str) -> tuple[list[tuple], list[tuple]]:
    b = f"arn:aws:s3:::{bucket}"
    allow = [("s3:PutObject", f"{b}/u/42/avatar.png", {}), ("s3:GetObject", f"{b}/u/42/avatar.png", {}),
             ("s3:ListBucket", b, {"s3:prefix": "u/42/"})]
    deny = [("s3:DeleteObject", f"{b}/u/42/avatar.png", {}), ("s3:GetObject", f"{b}/admin/export.csv", {}),
            ("s3:PutBucketPolicy", b, {}), ("s3:DeleteBucket", b, {}), ("s3:ListBucket", b, {"s3:prefix": ""}),
            ("s3:GetObject", "arn:aws:s3:::someone-elses-bucket/u/42/a.png", {}), ("s3:*", f"{b}/u/42/a.png", {}),
            ("iam:PassRole", "*", {})]
    return allow, deny


def check(folder: Path, bucket: str, after_cleanup: bool) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    if after_cleanup:
        doc = json.loads((folder / "after-cleanup.json").read_text(encoding="utf-8"))
        left = [m["ResourceARN"] for m in doc.get("ResourceTagMappingList", [])]
        out.append((not left, f"no resources tagged Project=lab08 remain ({len(left)} left)"))
        return out

    bdir = folder / "s3" / bucket
    out.append((bdir.is_dir(), f"s3/{bucket}/ exists"))
    if bdir.is_dir():
        findings = [(lvl, msg) for lvl, msg in sa.audit_bucket(bdir) if lvl != "INFO"]
        out.append((not findings, "s3_audit: no CRITICAL/WARN" + ("" if not findings else f" — {findings[0][1]}")))
    tags = {t["Key"]: t["Value"] for t in
            json.loads((folder / "bucket-tagging.json").read_text(encoding="utf-8")).get("TagSet", [])}
    out.append((tags.get("Project") == "lab08", f"bucket tagged Project=lab08 (got {tags.get('Project')})"))
    out.append((bool(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket)) and ".." not in bucket,
                "bucket name is valid (lowercase, 3–63)"))

    policy = json.loads((folder / "app-policy.json").read_text(encoding="utf-8"))
    lint = pl.lint_policy(policy, "app-policy")
    crit = [m for lvl, _, m in lint if lvl == 2]
    out.append((not crit, "policy_lint: no CRITICAL" + ("" if not crit else f" — {crit[0]}")))
    allow, deny = requests(bucket)
    for action, res, ctx in allow:
        d = pe.evaluate([policy], action, res, ctx)
        out.append((d.allowed, f"allowed: {action} {res.split(':::')[-1]} {ctx or ''} [{d.reason}]"))
    for action, res, ctx in deny:
        d = pe.evaluate([policy], action, res, ctx)
        out.append((not d.allowed, f"denied: {action} {res.split(':::')[-1]} {ctx or ''} [{d.reason}]"))

    text = (folder / "presign-results.txt").read_text(encoding="utf-8")
    before = re.search(r"^before:\s*(\d{3})", text, re.M)
    after = re.search(r"^after:\s*(\d{3})", text, re.M)
    out.append((bool(before) and before.group(1) == "200", "presigned URL worked before expiry (200)"))
    out.append((bool(after) and after.group(1) == "403", "presigned URL refused after expiry (403)"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--after-cleanup", action="store_true")
    a = ap.parse_args()
    try:
        results = check(a.folder, a.bucket, a.after_cleanup)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
