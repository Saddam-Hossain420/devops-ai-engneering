#!/usr/bin/env python3
"""make_budget.py — monthly cost budget ও ধাপে ধাপে alert-এর JSON file বানায়, এবং চালানোর `aws budgets` command ছাপে।
নিজে কোনো API call করে না — command আপনি দেখে-বুঝে চালাবেন।

  python3 make_budget.py --name monthly-learning --amount 10 --email you@example.com --out budget/
  # তারপর ছাপা command চালান (Budgets নিজে সাধারণত বিনামূল্যে, তবে সংখ্যা ও নিয়ম AWS-এর pricing page-এ দেখুন)

Alert: ACTUAL 50% · 80% · 100% এবং FORECASTED 100% — forecast মাসের শুরুতেই সতর্ক করে।
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
DEFAULT_ALERTS = (("ACTUAL", 50), ("ACTUAL", 80), ("ACTUAL", 100), ("FORECASTED", 100))


def budget_doc(name: str, amount: float, unit: str) -> dict:
    return {"BudgetName": name, "BudgetLimit": {"Amount": f"{amount:.2f}", "Unit": unit},
            "TimeUnit": "MONTHLY", "BudgetType": "COST"}


def notifications_doc(email: str, alerts: tuple[tuple[str, int], ...] = DEFAULT_ALERTS) -> list[dict]:
    return [{"Notification": {"NotificationType": kind, "ComparisonOperator": "GREATER_THAN",
                              "Threshold": float(pct), "ThresholdType": "PERCENTAGE"},
             "Subscribers": [{"SubscriptionType": "EMAIL", "Address": email}]}
            for kind, pct in alerts]


def validate(name: str, amount: float, email: str) -> None:
    if not NAME.match(name):
        raise ValueError("budget name: letters, digits, _ . - only")
    if not 0 < amount <= 100000:
        raise ValueError("amount must be a positive number you chose as your own limit")
    if not EMAIL.match(email):
        raise ValueError("email looks invalid")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Write budget + notification JSON for `aws budgets create-budget`.")
    ap.add_argument("--name", required=True)
    ap.add_argument("--amount", type=float, required=True, help="your own monthly limit (not a price)")
    ap.add_argument("--unit", default="USD")
    ap.add_argument("--email", required=True)
    ap.add_argument("--out", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    try:
        validate(a.name, a.amount, a.email)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    b, n = a.out / "budget.json", a.out / "notifications.json"
    b.write_text(json.dumps(budget_doc(a.name, a.amount, a.unit), indent=2) + "\n", encoding="utf-8")
    n.write_text(json.dumps(notifications_doc(a.email), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {b} and {n}")
    print("review both files, then run (account id: aws sts get-caller-identity --query Account --output text):")
    print(f"  aws budgets create-budget --account-id <ACCOUNT_ID> --budget file://{b.as_posix()} "
          f"--notifications-with-subscribers file://{n.as_posix()}")
    print(f"verify: aws budgets describe-notifications-for-budget --account-id <ACCOUNT_ID> --budget-name {a.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
