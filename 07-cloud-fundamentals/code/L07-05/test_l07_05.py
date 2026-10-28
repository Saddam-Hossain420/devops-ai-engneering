"""Tests for policy_eval.py ও policy_lint.py — চালানো: python3 -m unittest -v

প্রত্যাশাগুলো AWS IAM documentation-এর policy evaluation logic অনুযায়ী (identity policy অংশ)।
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import policy_eval as pe  # noqa: E402
import policy_lint as pl  # noqa: E402


def pol(*stmts: dict) -> dict:
    return {"Version": "2012-10-17", "Statement": list(stmts)}


def allowed(policies: list[dict], action: str, resource: str = "*", **ctx: str) -> bool:
    return pe.evaluate(policies, action, resource, {k.replace("_", ":"): v for k, v in ctx.items()}).allowed


class EvaluationTest(unittest.TestCase):
    def test_default_deny_and_explicit_deny_wins(self) -> None:
        self.assertFalse(allowed([], "s3:GetObject"))
        allow = pol({"Effect": "Allow", "Action": "s3:*", "Resource": "*"})
        deny = pol({"Effect": "Deny", "Action": "s3:DeleteObject", "Resource": "*"})
        self.assertTrue(allowed([allow], "s3:DeleteObject"))
        self.assertFalse(allowed([allow, deny], "s3:DeleteObject"))           # কোন policy আগে, তাতে কিছু যায় আসে না
        self.assertFalse(allowed([deny, allow], "s3:DeleteObject"))

    def test_wildcards_and_case(self) -> None:
        p = [pol({"Effect": "Allow", "Action": "s3:Get*", "Resource": "arn:aws:s3:::b/u/*"})]
        self.assertTrue(allowed(p, "S3:GETOBJECT", "arn:aws:s3:::b/u/x"))       # action case-insensitive
        self.assertFalse(allowed(p, "s3:GetObject", "arn:aws:s3:::b/U/x"))      # resource case-sensitive
        self.assertFalse(allowed(p, "s3:PutObject", "arn:aws:s3:::b/u/x"))
        q = [pol({"Effect": "Allow", "Action": "ec2:Describe?nstances", "Resource": "*"})]
        self.assertTrue(allowed(q, "ec2:DescribeInstances"))

    def test_not_action_and_not_resource(self) -> None:
        p = [pol({"Effect": "Allow", "NotAction": "iam:*", "Resource": "*"})]
        self.assertTrue(allowed(p, "ec2:TerminateInstances"))
        self.assertFalse(allowed(p, "iam:CreateUser"))
        q = [pol({"Effect": "Allow", "Action": "s3:*", "NotResource": "arn:aws:s3:::secret/*"})]
        self.assertFalse(allowed(q, "s3:GetObject", "arn:aws:s3:::secret/x"))

    def test_conditions(self) -> None:
        mfa = [pol({"Effect": "Allow", "Action": "iam:*", "Resource": "*",
                    "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}}})]
        self.assertTrue(allowed(mfa, "iam:CreateUser", aws_MultiFactorAuthPresent="true"))
        self.assertFalse(allowed(mfa, "iam:CreateUser"))                         # key নেই → শর্ত মিথ্যা
        ip = [pol({"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*",
                   "Condition": {"IpAddress": {"aws:SourceIp": ["203.0.113.0/24", "198.51.100.7/32"]}}})]
        self.assertTrue(allowed(ip, "s3:GetObject", aws_SourceIp="198.51.100.7"))
        self.assertFalse(allowed(ip, "s3:GetObject", aws_SourceIp="192.0.2.1"))
        deny_if = [pol({"Effect": "Allow", "Action": "*", "Resource": "*"}),
                   pol({"Effect": "Deny", "Action": "iam:*", "Resource": "*",
                        "Condition": {"BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}}})]
        self.assertFalse(allowed(deny_if, "iam:CreateUser"))                     # IfExists: key নেই → শর্ত সত্য → deny
        self.assertTrue(allowed(deny_if, "iam:CreateUser", aws_MultiFactorAuthPresent="true"))

    def test_sample_requests_match_expectations(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = pe.main([str(HERE / "taskflow-app.json"), "--requests", str(HERE / "requests.json")])
        self.assertEqual(code, 0, out.getvalue())


class LintTest(unittest.TestCase):
    def levels(self, policy: dict) -> list[int]:
        return [f[0] for f in pl.lint_policy(policy, "t")]

    def test_samples(self) -> None:
        good = json.loads((HERE / "taskflow-app.json").read_text(encoding="utf-8"))
        bad = json.loads((HERE / "dev-admin.json").read_text(encoding="utf-8"))
        self.assertEqual(pl.lint_policy(good, "good"), [])
        self.assertEqual(sorted(self.levels(bad)), [1, 2, 2])

    def test_not_action_admin_is_critical(self) -> None:
        # regression: NotAction + "*" যদি iam/sts/kms বাদ না দেয়, তা কার্যত admin — আগে শুধু warning দিত
        p = pol({"Effect": "Allow", "NotAction": ["budgets:*"], "Resource": "*"})
        self.assertEqual(self.levels(p), [2])
        q = pol({"Effect": "Allow", "NotAction": ["iam:*", "sts:*", "kms:*", "organizations:*"], "Resource": "*"})
        self.assertEqual(self.levels(q), [1])

    def test_other_rules(self) -> None:
        self.assertEqual(self.levels(pol({"Effect": "Allow", "Action": "*", "Resource": "*"})), [2])
        self.assertIn(2, self.levels(pol({"Effect": "Allow", "Action": "iam:*", "Resource": "*"})))
        self.assertEqual(self.levels(pol({"Effect": "Allow", "Action": "ec2:TerminateInstances", "Resource": "*"})), [1])
        self.assertEqual(self.levels(pol({"Effect": "Allow", "Principal": "*", "Action": "s3:GetObject",
                                          "Resource": "arn:aws:s3:::b/*"})), [2])
        self.assertEqual(self.levels(pol({"Effect": "Deny", "Action": "*", "Resource": "*"})), [])


if __name__ == "__main__":
    unittest.main()
