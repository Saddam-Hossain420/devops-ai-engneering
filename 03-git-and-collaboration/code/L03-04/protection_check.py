#!/usr/bin/env python3
"""Branch protection policy check — GitHub-এর `GET /repos/{owner}/{repo}/branches/{branch}/protection`
API-র JSON একটি ন্যূনতম policy-র সাথে মেলায়। Read-only; কিছু বদলায় না।

  gh api repos/OWNER/REPO/branches/main/protection > protection.json    # আসল JSON (admin অধিকার লাগে)
  python3 protection_check.py protection.json
  python3 protection_check.py sample-protection.json --min-approvals 2

Exit: 0 policy পূরণ, 1 ঘাটতি, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def enabled(data: dict, key: str) -> bool:
    """API অনেক setting `{"enabled": true}` আকারে দেয়; অনুপস্থিত = বন্ধ।"""
    v = data.get(key)
    return bool(v.get("enabled")) if isinstance(v, dict) else bool(v)


def check(data: dict, min_approvals: int, required_checks: list[str]) -> list[tuple[bool, str]]:
    reviews = data.get("required_pull_request_reviews") or {}
    status = data.get("required_status_checks") or {}
    contexts = set(status.get("contexts") or []) | {c.get("context") for c in status.get("checks") or []}
    results = [
        (bool(reviews), "pull request required before merging"),
        (reviews.get("required_approving_review_count", 0) >= min_approvals,
         f"at least {min_approvals} approving review(s) "
         f"(has {reviews.get('required_approving_review_count', 0)})"),
        (bool(reviews.get("dismiss_stale_reviews")), "new commits dismiss stale approvals"),
        (bool(reviews.get("require_code_owner_reviews")), "code owner review required (CODEOWNERS enforced)"),
        (bool(status), "status checks required"),
        (bool(status.get("strict")), "branch must be up to date with base before merging"),
        (enabled(data, "enforce_admins"), "rules apply to administrators too"),
        (not enabled(data, "allow_force_pushes"), "force push disabled"),
        (not enabled(data, "allow_deletions"), "branch deletion disabled"),
        (enabled(data, "required_conversation_resolution"), "review conversations must be resolved"),
    ]
    for name in required_checks:
        results.append((name in contexts, f"required check {name!r} configured"))
    return results


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Compare branch protection JSON to a minimum policy.")
    ap.add_argument("file", type=Path)
    ap.add_argument("--min-approvals", type=int, default=1)
    ap.add_argument("--require-check", action="append", default=[])
    args = ap.parse_args(argv)
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("expected a JSON object")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    results = check(data, args.min_approvals, args.require_check)
    for ok, text in results:
        print(f"{'PASS' if ok else 'FAIL'}  {text}")
    failed = sum(not ok for ok, _ in results)
    print(f"{len(results) - failed}/{len(results)} policy items met")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
