"""Tests for trust_policy_lint.py — চালানো: python3 -m unittest -v (হাতে তৈরি role, কোনো AWS call নেই)"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import trust_policy_lint as tl  # noqa: E402

S = HERE / "sample"
GH = "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"


def role(statement: dict, **kw: object) -> dict:
    return {"RoleName": "r", "AssumeRolePolicyDocument": {"Statement": [statement]}, **kw}


def gh(cond: dict) -> dict:
    return role({"Effect": "Allow", "Principal": {"Federated": GH}, "Action": "sts:AssumeRoleWithWebIdentity",
                 "Condition": cond})


def levels(r: dict, account: str | None = "111122223333") -> list[str]:
    return [lvl for lvl, _ in tl.lint_role(r, account)]


class TrustLintTest(unittest.TestCase):
    def test_samples(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = tl.main([str(p) for p in sorted(S.glob("role-*.json"))] + ["--account", "111122223333",
                         "--instance-profile", str(S / "instance-profile-taskflow.json")])
        self.assertEqual(rc, 1)
        self.assertIn("3 role(s): 1 critical, 2 warning(s)", out.getvalue())
        self.assertIn("no findings: taskflow-app", out.getvalue())

    def test_github_sub_conditions(self) -> None:
        aud = {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"}
        pinned = gh({"StringEquals": aud | {"token.actions.githubusercontent.com:sub":
                                            "repo:acme/taskflow:ref:refs/heads/main"}})
        self.assertEqual(levels(pinned), [])
        branch_any = gh({"StringEquals": aud, "StringLike": {"token.actions.githubusercontent.com:sub": "repo:acme/taskflow:*"}})
        self.assertEqual(levels(branch_any), ["WARN"])
        every_repo = gh({"StringEquals": aud, "StringLike": {"token.actions.githubusercontent.com:sub": "repo:*"}})
        self.assertEqual(levels(every_repo), ["CRITICAL"])
        self.assertIn("CRITICAL", levels(gh({"StringEquals": aud})))

    def test_principal_star_forms(self) -> None:
        for principal in ("*", {"AWS": "*"}, {"AWS": ["arn:aws:iam::111122223333:root", "*"]}):
            r = role({"Effect": "Allow", "Principal": principal, "Action": "sts:AssumeRole"})
            self.assertEqual(levels(r)[0], "CRITICAL", principal)

    def test_own_vs_cross_account(self) -> None:
        own = role({"Effect": "Allow", "Principal": {"AWS": "111122223333"}, "Action": "sts:AssumeRole"})
        self.assertEqual(levels(own), ["INFO"])
        other = role({"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::444455556666:root"}, "Action": "sts:AssumeRole",
                      "Condition": {"StringEquals": {"sts:ExternalId": "abc-123"}}})
        self.assertEqual(levels(other), [])                                       # ExternalId থাকলে ঠিক

    def test_url_encoded_document(self) -> None:
        r = json.loads((S / "role-partner-audit.json").read_text(encoding="utf-8"))["Role"]
        self.assertEqual(tl.trust_doc(r)["Statement"][0]["Principal"], {"AWS": "arn:aws:iam::444455556666:root"})

    def test_instance_profile(self) -> None:
        prof = json.loads((S / "instance-profile-taskflow.json").read_text(encoding="utf-8"))
        lam = role({"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"})
        lam["RoleName"] = "taskflow-app"
        self.assertEqual(tl.check_instance_profile(prof, {"taskflow-app": lam})[0][0], "CRITICAL")
        app = json.loads((S / "role-taskflow-app.json").read_text(encoding="utf-8"))["Role"]
        self.assertEqual(tl.check_instance_profile(prof, {"taskflow-app": app}), [])


if __name__ == "__main__":
    unittest.main()
