#!/usr/bin/env python3
"""account_baseline.py — AWS account-এর প্রথম দিনের নিরাপত্তা যাচাই, AWS CLI-র saved output থেকে (offline, শুধু পড়ে)।

  aws iam get-account-summary > account-summary.json
  aws iam generate-credential-report; aws iam get-credential-report --query Content --output text | base64 -d > credential-report.csv
  aws budgets describe-budgets --account-id <ID> > budgets.json
  aws budgets describe-notifications-for-budget --account-id <ID> --budget-name <NAME> > notifications-<NAME>.json

  python3 account_baseline.py --summary account-summary.json --report credential-report.csv \
      --budgets budgets.json --notifications notifications-*.json --today 2026-10-28

খোঁজে: root-এ MFA নেই · root-এর access key · root সম্প্রতি ব্যবহৃত · console password আছে কিন্তু MFA নেই ·
পুরোনো বা কখনো-ব্যবহৃত-না access key · budget নেই · budget-এ ACTUAL/FORECASTED alert নেই।
Exit: 0 সব ঠিক, 1 finding আছে, 2 input error। এই script কোনো AWS API call করে না।
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

CRIT, WARN = 2, 1
ROOT = "<root_account>"


@dataclass
class Finding:
    level: int
    subject: str
    message: str


def parse_day(value: str) -> date | None:
    """Credential report-এর তারিখ (ISO 8601) — 'N/A', 'no_information', 'not_supported' হলে None।"""
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def check_summary(summary: dict) -> list[Finding]:
    m = summary.get("SummaryMap", {})
    out = []
    if m.get("AccountMFAEnabled") != 1:
        out.append(Finding(CRIT, "root", "root user has no MFA — enable it before anything else"))
    if m.get("AccountAccessKeysPresent"):
        out.append(Finding(CRIT, "root", "root user has access keys — delete them (root keys cannot be limited by IAM)"))
    return out


def check_report(rows: list[dict[str, str]], today: date, key_max_age: int, root_recent_days: int) -> list[Finding]:
    out = []
    for r in rows:
        who = "root" if r["user"] == ROOT else r["user"]
        if r["user"] == ROOT:
            if r.get("mfa_active") != "true":
                out.append(Finding(CRIT, who, "root user has no MFA — credential report: mfa_active=false"))
            used = parse_day(r.get("password_last_used", ""))
            if used and (today - used).days <= root_recent_days:
                out.append(Finding(WARN, who, f"root signed in {(today - used).days} day(s) ago — use an admin user/role for daily work"))
        elif r.get("password_enabled") == "true" and r.get("mfa_active") != "true":
            out.append(Finding(WARN, who, "console password without MFA"))
        for n in ("1", "2"):
            if r.get(f"access_key_{n}_active") != "true":
                continue
            if r["user"] == ROOT:
                out.append(Finding(CRIT, who, f"root user has access keys — key {n} active (credential report)"))
                continue
            rotated = parse_day(r.get(f"access_key_{n}_last_rotated", ""))
            last_used = parse_day(r.get(f"access_key_{n}_last_used_date", ""))
            if rotated and (today - rotated).days > key_max_age:
                out.append(Finding(WARN, who, f"access key {n} is {(today - rotated).days} days old (> {key_max_age}) — "
                                              "rotate, or better: replace with a role/SSO"))
            if last_used is None and rotated and (today - rotated).days > 30:
                out.append(Finding(WARN, who, f"access key {n} never used in {(today - rotated).days} days — deactivate it"))
    return out


def check_budgets(budgets: dict | None, notifications: dict[str, dict]) -> list[Finding]:
    items = (budgets or {}).get("Budgets", [])
    if not items:
        return [Finding(CRIT, "billing", "no budget — create one before launching anything (make_budget.py)")]
    out = []
    for b in items:
        name = b["BudgetName"]
        kinds = {n["NotificationType"] for n in notifications.get(name, {}).get("Notifications", [])}
        for kind, why in (("ACTUAL", "tells you after money is spent"),
                          ("FORECASTED", "warns early, while the month is still young")):
            if kind not in kinds:
                out.append(Finding(WARN, f"budget {name}", f"no {kind} notification ({why})"))
    return out


def load_notifications(paths: list[Path]) -> dict[str, dict]:
    """File-এর নাম notifications-<BUDGET>.json — budget-এর নাম নামেই থাকে, কারণ API output-এ নাম নেই।"""
    out = {}
    for p in paths:
        stem = p.stem
        if not stem.startswith("notifications-"):
            raise ValueError(f"{p.name}: name it notifications-<budget-name>.json")
        out[stem[len("notifications-"):]] = json.loads(p.read_text(encoding="utf-8"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="AWS account day-one safety baseline (offline, read-only).")
    ap.add_argument("--summary", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--budgets", type=Path)
    ap.add_argument("--notifications", type=Path, nargs="*", default=[])
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--key-max-age", type=int, default=90)
    ap.add_argument("--root-recent-days", type=int, default=30)
    a = ap.parse_args(argv)
    try:
        findings: list[Finding] = []
        if a.summary:
            findings += check_summary(json.loads(a.summary.read_text(encoding="utf-8")))
        if a.report:
            with a.report.open(encoding="utf-8", newline="") as f:
                findings += check_report(list(csv.DictReader(f)), a.today, a.key_max_age, a.root_recent_days)
        budgets = json.loads(a.budgets.read_text(encoding="utf-8")) if a.budgets else None
        findings += check_budgets(budgets, load_notifications(a.notifications))
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    # একই সমস্যা summary ও report দুই জায়গা থেকে এলে একবার দেখানো
    seen, unique = set(), []
    for f in sorted(findings, key=lambda f: (-f.level, f.subject)):
        key = (f.subject, f.message.split(" — ")[0])
        if key not in seen:
            seen.add(key)
            unique.append(f)
    for f in unique:
        print(f"{'CRITICAL' if f.level == CRIT else 'WARN':<8}  {f.subject:<26} {f.message}")
    crit = sum(f.level == CRIT for f in unique)
    print(f"{len(unique)} finding(s), {crit} critical" if unique else "baseline OK")
    return 1 if unique else 0


if __name__ == "__main__":
    raise SystemExit(main())
