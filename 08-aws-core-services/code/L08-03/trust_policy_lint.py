#!/usr/bin/env python3
"""trust_policy_lint.py — IAM role-এর trust policy (কে এই role assume করতে পারে) যাচাই; offline, শুধু পড়ে।

  aws iam get-role --role-name github-deploy > role-github-deploy.json
  python3 trust_policy_lint.py role-*.json --account 111122223333
  python3 trust_policy_lint.py role-taskflow-app.json --instance-profile instance-profile-taskflow.json

Permission policy বলে role কী করতে পারে (L07-05); trust policy বলে **কে** role হতে পারে — দুটোই সমান গুরুত্বপূর্ণ।
খোঁজে: Principal "*" · অন্য account-কে ExternalId/PrincipalOrgID ছাড়া trust · GitHub OIDC-তে `sub`/`aud` condition নেই
বা `sub`-এ ঢালাও wildcard · `sts:*` · লম্বা session · instance profile-এর role-এ ec2.amazonaws.com trust নেই।
Exit: 0 কোনো CRITICAL নেই, 1 CRITICAL আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

CRIT, WARN, INFO = "CRITICAL", "WARN", "INFO"
GITHUB = "token.actions.githubusercontent.com"
ASSUME_ACTIONS = {"sts:assumerole", "sts:assumerolewithwebidentity", "sts:assumerolewithsaml", "sts:*", "*"}


def as_list(x: Any) -> list[Any]:
    return x if isinstance(x, list) else [x]


def trust_doc(role: dict[str, Any]) -> dict[str, Any]:
    """get-role-এর AssumeRolePolicyDocument — CLI সাধারণত JSON object দেয়, API URL-encoded string।"""
    doc = role["AssumeRolePolicyDocument"]
    return json.loads(urllib.parse.unquote(doc)) if isinstance(doc, str) else doc


def cond_values(cond: dict[str, Any], key: str) -> list[tuple[str, str]]:
    """Condition-এর ভেতরে key খুঁজে (operator, value) জোড়া — key-এর case উপেক্ষা।"""
    out = []
    for op, pairs in cond.items():
        for k, v in pairs.items():
            if k.lower() == key.lower():
                out += [(op, str(x)) for x in as_list(v)]
    return out


def principals(stmt: dict[str, Any], kind: str) -> list[str]:
    """Principal-এর একটি ধরন (AWS/Service/Federated)-এর তালিকা; `"Principal": "*"` মানে AWS "*"।"""
    p = stmt.get("Principal", {})
    if not isinstance(p, dict):
        p = {"AWS": p}
    return [str(x) for x in as_list(p.get(kind, []))]


def account_of(principal: str) -> str | None:
    if principal.isdigit() and len(principal) == 12:
        return principal
    parts = principal.split(":")
    return parts[4] if principal.startswith("arn:") and len(parts) > 4 else None


def lint_role(role: dict[str, Any], own_account: str | None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if role.get("MaxSessionDuration", 3600) > 4 * 3600:
        out.append((WARN, f"MaxSessionDuration {role['MaxSessionDuration'] // 3600} h — stolen session lasts that long"))
    for s in as_list(trust_doc(role).get("Statement", [])):
        if s.get("Effect") != "Allow":
            continue
        actions = {a.lower() for a in as_list(s.get("Action", []))}
        if not actions & ASSUME_ACTIONS:
            continue
        if actions & {"sts:*", "*"}:
            out.append((WARN, f"Action {sorted(actions)} — list the exact sts action"))
        cond = s.get("Condition", {}) or {}
        if "*" in principals(s, "AWS"):
            out.append((CRIT, "Principal \"*\" — any AWS identity anywhere can try to assume this role"))
            continue
        for p in principals(s, "AWS"):
            acct = account_of(p)
            if own_account and acct == own_account:
                if p.endswith(":root") or p == acct:
                    out.append((INFO, "trusts this whole account — any principal here whose own policy allows "
                                      "sts:AssumeRole can use it"))
            elif acct:
                if not (cond_values(cond, "sts:ExternalId") or cond_values(cond, "aws:PrincipalOrgID")):
                    out.append((WARN, f"cross-account trust to {acct} without sts:ExternalId or aws:PrincipalOrgID "
                                      "(confused-deputy risk for third parties)"))
        for fed in principals(s, "Federated"):
            if fed.endswith(f"oidc-provider/{GITHUB}"):
                aud = cond_values(cond, f"{GITHUB}:aud")
                sub = cond_values(cond, f"{GITHUB}:sub")
                if not sub:
                    out.append((CRIT, "GitHub OIDC trust without a 'sub' condition — any repository on GitHub "
                                      "can assume this role"))
                for op, value in sub:
                    if value in ("*", "repo:*") or value.startswith("repo:*"):
                        out.append((CRIT, f"GitHub 'sub' {op} '{value}' — matches every repository"))
                    elif "*" in value or "?" in value:
                        out.append((WARN, f"GitHub 'sub' {op} '{value}' — wildcard matches more repos/branches/PRs "
                                          "than intended; pin repo and ref or environment"))
                if not any(v == "sts.amazonaws.com" for _, v in aud):
                    out.append((WARN, "GitHub OIDC trust without aud = sts.amazonaws.com"))
    return out


def check_instance_profile(profile: dict[str, Any], roles: dict[str, dict[str, Any]]) -> list[tuple[str, str]]:
    ip = profile["InstanceProfile"]
    out: list[tuple[str, str]] = []
    if len(ip.get("Roles", [])) != 1:
        out.append((CRIT, f"instance profile {ip['InstanceProfileName']} has {len(ip.get('Roles', []))} roles (needs exactly 1)"))
    for r in ip.get("Roles", []):
        role = roles.get(r["RoleName"])
        if role is None:
            out.append((WARN, f"role {r['RoleName']} not given — cannot check its trust policy"))
            continue
        services = {svc for s in as_list(trust_doc(role).get("Statement", [])) if s.get("Effect") == "Allow"
                    for svc in principals(s, "Service")}
        if "ec2.amazonaws.com" not in services:
            out.append((CRIT, f"role {r['RoleName']} does not trust ec2.amazonaws.com — instances get no credentials"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint IAM role trust policies (offline).")
    ap.add_argument("roles", nargs="+", type=Path, help="files from `aws iam get-role`")
    ap.add_argument("--account", help="your account id (to tell own-account from cross-account trust)")
    ap.add_argument("--instance-profile", type=Path, action="append", default=[])
    a = ap.parse_args(argv)
    try:
        roles = {}
        for path in a.roles:
            role = json.loads(path.read_text(encoding="utf-8"))["Role"]
            roles[role["RoleName"]] = role
        results = [(name, lvl, msg) for name, role in roles.items() for lvl, msg in lint_role(role, a.account)]
        for p in a.instance_profile:
            prof = json.loads(p.read_text(encoding="utf-8"))
            results += [(f"profile:{prof['InstanceProfile']['InstanceProfileName']}", lvl, msg)
                        for lvl, msg in check_instance_profile(prof, roles)]
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for name, lvl, msg in sorted(results, key=lambda r: ({CRIT: 0, WARN: 1, INFO: 2}[r[1]], r[0])):
        print(f"{lvl:<8}  {name:<26} {msg}")
    clean = sorted(set(roles) - {n for n, lvl, _ in results if lvl != INFO})
    if clean:
        print("no findings: " + ", ".join(clean))
    crit = sum(lvl == CRIT for _, lvl, _ in results)
    print(f"{len(roles)} role(s): {crit} critical, {sum(lvl == WARN for _, lvl, _ in results)} warning(s)")
    return 1 if crit else 0


if __name__ == "__main__":
    raise SystemExit(main())
