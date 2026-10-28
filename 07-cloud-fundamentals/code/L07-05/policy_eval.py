#!/usr/bin/env python3
"""policy_eval.py — AWS-ধাঁচের identity policy-র সিদ্ধান্ত হিসাব (শেখার জন্য; কোনো API call নেই)।

  python3 policy_eval.py taskflow-app.json --action s3:GetObject --resource arn:aws:s3:::taskflow-uploads/u/1.png
  python3 policy_eval.py dev-admin.json --action iam:CreateUser --resource '*' --context aws:MultiFactorAuthPresent=false
  python3 policy_eval.py taskflow-app.json --requests requests.json      # অনেক request একসাথে

নিয়ম (AWS IAM documentation-এর "policy evaluation logic"-এর identity-policy অংশ):
  default = implicit deny; কোনো Allow statement মিললে allow; কিন্তু কোনো Deny statement মিললে সবসময় deny।
  Action/NotAction, Resource/NotResource; wildcard * ও ? (action case-insensitive, resource case-sensitive)।
  Condition: StringEquals, StringNotEquals, StringLike, Bool, IpAddress, NotIpAddress, NumericLessThan(Equals);
  `…IfExists` — key না থাকলে শর্ত সত্য। একাধিক key = AND, একটি key-র একাধিক মান = OR।
সীমা: resource policy, permission boundary, SCP, session policy এখানে নেই — শুধু identity policy।
"""
from __future__ import annotations

import argparse
import fnmatch
import ipaddress
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Decision:
    allowed: bool
    reason: str


def as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else [x]


def wildcard(pattern: str, value: str, case_sensitive: bool) -> bool:
    regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
    return re.fullmatch(regex, value, 0 if case_sensitive else re.IGNORECASE) is not None


def action_matches(stmt: Mapping[str, Any], action: str) -> bool:
    if "NotAction" in stmt:
        return not any(wildcard(p, action, False) for p in as_list(stmt["NotAction"]))
    return any(wildcard(p, action, False) for p in as_list(stmt.get("Action", [])))


def resource_matches(stmt: Mapping[str, Any], resource: str) -> bool:
    if "NotResource" in stmt:
        return not any(wildcard(p, resource, True) for p in as_list(stmt["NotResource"]))
    return any(wildcard(p, resource, True) for p in as_list(stmt.get("Resource", [])))


def condition_ok(cond: Mapping[str, Mapping[str, Any]], ctx: Mapping[str, str]) -> bool:
    for op, pairs in cond.items():
        if_exists = op.endswith("IfExists")
        base = op[: -len("IfExists")] if if_exists else op
        for key, values in pairs.items():
            if key not in ctx:
                if if_exists:
                    continue
                return False                              # key নেই → শর্ত মিথ্যা (Not… সহ, documentation অনুযায়ী)
            actual = ctx[key]
            vals = [str(v) for v in as_list(values)]
            if base == "StringEquals":
                ok = actual in vals
            elif base == "StringNotEquals":
                ok = actual not in vals
            elif base == "StringLike":
                ok = any(fnmatch.fnmatchcase(actual, v) for v in vals)
            elif base == "Bool":
                ok = actual.lower() in [v.lower() for v in vals]
            elif base in ("IpAddress", "NotIpAddress"):
                inside = any(ipaddress.ip_address(actual) in ipaddress.ip_network(v, strict=False) for v in vals)
                ok = inside if base == "IpAddress" else not inside
            elif base in ("NumericLessThan", "NumericLessThanEquals"):
                ok = any(float(actual) < float(v) if base == "NumericLessThan" else float(actual) <= float(v)
                         for v in vals)
            else:
                raise ValueError(f"unsupported condition operator {op}")
            if not ok:
                return False
    return True


def evaluate(policies: list[Mapping[str, Any]], action: str, resource: str,
             ctx: Mapping[str, str] | None = None) -> Decision:
    ctx = ctx or {}
    allow_by = None
    for p_index, policy in enumerate(policies):
        for s_index, stmt in enumerate(as_list(policy.get("Statement", []))):
            if not (action_matches(stmt, action) and resource_matches(stmt, resource)):
                continue
            if "Condition" in stmt and not condition_ok(stmt["Condition"], ctx):
                continue
            label = stmt.get("Sid") or f"policy {p_index} statement {s_index}"
            if stmt.get("Effect") == "Deny":
                return Decision(False, f"explicit deny by {label}")
            if stmt.get("Effect") == "Allow" and allow_by is None:
                allow_by = label
    if allow_by:
        return Decision(True, f"allowed by {allow_by}")
    return Decision(False, "implicit deny (no statement allows it)")


def parse_ctx(items: list[str]) -> dict[str, str]:
    return dict(i.split("=", 1) for i in items)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Evaluate AWS-style identity policies (learning tool).")
    ap.add_argument("policies", nargs="+", type=Path)
    ap.add_argument("--action")
    ap.add_argument("--resource", default="*")
    ap.add_argument("--context", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--requests", type=Path, help="JSON list of {action, resource, context, expect?}")
    a = ap.parse_args(argv)
    try:
        policies = [json.loads(p.read_text(encoding="utf-8")) for p in a.policies]
        reqs = (json.loads(a.requests.read_text(encoding="utf-8")) if a.requests
                else [{"action": a.action, "resource": a.resource, "context": parse_ctx(a.context)}])
        if any(r.get("action") is None for r in reqs):
            ap.error("--action or --requests is required")
        mismatches = 0
        for r in reqs:
            d = evaluate(policies, r["action"], r.get("resource", "*"), r.get("context", {}))
            mark = ""
            if "expect" in r:
                ok = (r["expect"] == "allow") == d.allowed
                mismatches += not ok
                mark = "  ✓" if ok else f"  ✗ expected {r['expect']}"
            print(f"{'ALLOW' if d.allowed else 'DENY ':<5} {r['action']:<24} {r.get('resource', '*'):<48} {d.reason}{mark}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
