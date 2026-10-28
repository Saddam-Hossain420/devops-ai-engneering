"""Tests for account_baseline.py ও make_budget.py — চালানো: python3 -m unittest -v (হাতে তৈরি নমুনা, কোনো AWS call নেই)"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import account_baseline as ab  # noqa: E402
import make_budget as mb  # noqa: E402

TODAY = date(2026, 10, 28)
S = HERE / "sample"


def rows() -> list[dict[str, str]]:
    with (S / "credential-report.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


class BaselineTest(unittest.TestCase):
    def test_sample_findings(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = ab.main(["--summary", str(S / "account-summary.json"), "--report", str(S / "credential-report.csv"),
                          "--budgets", str(S / "budgets.json"),
                          "--notifications", str(S / "notifications-monthly-learning.json"), "--today", "2026-10-28"])
        text = out.getvalue()
        self.assertEqual(rc, 1)
        self.assertIn("8 finding(s), 2 critical", text)                         # summary ও report-এর একই সমস্যা একবার
        self.assertEqual(text.count("root user has no MFA"), 1)

    def test_secure_root_and_users(self) -> None:
        r = rows()
        r[0].update(mfa_active="true", access_key_1_active="false", password_last_used="2026-06-01T00:00:00+00:00")  # scan-secrets: allow — তারিখ, password নয়
        r[1].update(mfa_active="true", access_key_1_last_rotated="2026-09-01T00:00:00+00:00")
        r[2]["access_key_1_active"] = "false"
        self.assertEqual(ab.check_report(r, TODAY, 90, 30), [])
        ok = {"SummaryMap": {"AccountMFAEnabled": 1, "AccountAccessKeysPresent": 0}}
        self.assertEqual(ab.check_summary(ok), [])

    def test_special_values_are_not_dates(self) -> None:
        for v in ("N/A", "no_information", "not_supported", ""):
            self.assertIsNone(ab.parse_day(v))
        self.assertEqual(ab.parse_day("2026-10-25T18:30:00+00:00"), date(2026, 10, 25))

    def test_budget_checks(self) -> None:
        self.assertEqual(ab.check_budgets(None, {})[0].level, ab.CRIT)
        budgets = json.loads((S / "budgets.json").read_text(encoding="utf-8"))
        both = {"monthly-learning": {"Notifications": [{"NotificationType": "ACTUAL"}, {"NotificationType": "FORECASTED"}]}}
        self.assertEqual(ab.check_budgets(budgets, both), [])
        with self.assertRaisesRegex(ValueError, "notifications-<budget-name>"):
            ab.load_notifications([S / "budgets.json"])


class MakeBudgetTest(unittest.TestCase):
    def test_files_and_alerts(self) -> None:
        with tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()):
            self.assertEqual(mb.main(["--name", "lab", "--amount", "5", "--email", "me@example.com", "--out", d]), 0)
            b = json.loads(Path(d, "budget.json").read_text(encoding="utf-8"))
            n = json.loads(Path(d, "notifications.json").read_text(encoding="utf-8"))
        self.assertEqual(b["BudgetLimit"], {"Amount": "5.00", "Unit": "USD"})
        self.assertEqual([x["Notification"]["NotificationType"] for x in n], ["ACTUAL", "ACTUAL", "ACTUAL", "FORECASTED"])
        # make_budget-এর output account_baseline-এর budget check পাস করে
        notes = {"lab": {"Notifications": [x["Notification"] for x in n]}}
        self.assertEqual(ab.check_budgets({"Budgets": [b]}, notes), [])

    def test_rejects_bad_input(self) -> None:
        for name, amount, email in (("bad name", 5, "a@b.co"), ("ok", 0, "a@b.co"), ("ok", 5, "not-an-email")):
            with self.assertRaises(ValueError):
                mb.validate(name, amount, email)


if __name__ == "__main__":
    unittest.main()
