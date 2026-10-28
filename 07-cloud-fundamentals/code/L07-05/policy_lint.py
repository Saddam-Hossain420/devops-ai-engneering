#!/usr/bin/env python3
"""policy_lint.py — AWS-ধাঁচের IAM policy-তে অতিরিক্ত অনুমতি ও privilege-escalation-এর ঝুঁকি খোঁজা।

  python3 policy_lint.py dev-admin.json taskflow-app.json

Critical: Allow Action "*"; Allow "<service>:*" on "*" for iam/sts/kms/organizations; iam:PassRole বা
          sts:AssumeRole on "*"; resource policy-তে Principal "*" শর্ত ছাড়া; escalation-এর পরিচিত action ("*" resource-এ)।
Warning:  Allow + NotAction / NotResource; write/delete action on Resource "*"; service-wide wildcard ("s3:*");
          iam:* / kms:* -এ MFA শর্ত নেই।
Exit: 0 কিছু নেই, 1 warning, 2 critical।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SENSITIVE_SERVICES = {"iam", "sts", "kms", "organizations"}
ESCALATION = {"iam:passrole", "sts:assumerole", "iam:createpolicyversion", "iam:attachuserpolicy",
              "iam:attachrolepolicy", "iam:putuserpolicy", "iam:putrolepolicy", "iam:createaccesskey",
              "iam:updateassumerolepolicy", "lambda:updatefunctioncode"}
WRITE_VERBS = ("put", "delete", "create", "update", "attach", "detach", "terminate", "modify", "write", "remove")


def as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else [x]


def lint_policy(policy: dict[str, Any], name: str) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []
    for i, s in enumerate(as_list(policy.get("Statement", []))):
        sid = s.get("Sid") or f"#{i}"
        where = f"{name} {sid}"
        if s.get("Effect") != "Allow":
            continue
        actions = [a.lower() for a in as_list(s.get("Action", []))]
        resources = as_list(s.get("Resource", []))
        star_res = "*" in resources
        has_cond = bool(s.get("Condition"))
        principal = s.get("Principal")
        if principal == "*" or (isinstance(principal, dict) and "*" in as_list(principal.get("AWS", []))):
            if not has_cond:
                out.append((2, where, "Principal \"*\" without a condition — anyone (any account) can use this"))
        if "NotAction" in s:
            excluded = {a.lower().split(":")[0] for a in as_list(s["NotAction"]) if a.lower().endswith(":*")}
            if star_res and not SENSITIVE_SERVICES <= excluded:
                left = ", ".join(sorted(SENSITIVE_SERVICES - excluded))
                out.append((2, where, f"Allow + NotAction on \"*\" — effectively administrator ({left} still allowed)"))
            else:
                out.append((1, where, "Allow with NotAction grants everything except the list — new services are allowed automatically"))
        if "NotResource" in s:
            out.append((1, where, "Allow with NotResource — applies to every resource except the list"))
        if "*" in actions:
            out.append((2, where, "Action \"*\" — full administrator"))
            continue
        for a in actions:
            service, _, verb = a.partition(":")
            if verb == "*" and star_res and service in SENSITIVE_SERVICES:
                out.append((2, where, f"{a} on \"*\" — can grant itself any permission"))
            elif verb == "*":
                out.append((1, where, f"{a} — every action of {service}, including delete; list the actions needed"))
            if a in ESCALATION and star_res:
                out.append((2, where, f"{a} on \"*\" — known privilege-escalation path; scope the resource"))
            elif star_res and verb != "*" and verb.startswith(WRITE_VERBS) and not has_cond:
                out.append((1, where, f"{a} on \"*\" — write/delete on every resource"))
            if service in ("iam", "kms") and verb == "*" and not has_cond:
                out.append((1, where, f"{a} without an MFA/source condition"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Find over-broad permissions in IAM policies.")
    ap.add_argument("policies", nargs="+", type=Path)
    a = ap.parse_args(argv)
    worst = 0
    for path in a.policies:
        try:
            findings = lint_policy(json.loads(path.read_text(encoding="utf-8")), path.name)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            return 2
        for level, where, msg in findings:
            print(f"{'CRIT' if level == 2 else 'WARN'}  {where:<34} {msg}")
            worst = max(worst, level)
        if not findings:
            print(f"ok    {path.name}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
