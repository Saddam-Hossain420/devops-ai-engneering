"""Tests for presign.py ও s3_audit.py — চালানো: python3 -m unittest -v (কোনো network/AWS call নেই)"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import presign as ps  # noqa: E402
import s3_audit as sa  # noqa: E402

S = HERE / "sample"
# AWS S3 documentation-এর "Authenticating Requests: Using Query Parameters (AWS Signature Version 4)"-এর প্রকাশিত উদাহরণ
DOC_KEY_ID = "AKIAIOSFODNN7EXAMPLE"  # scan-secrets: allow — AWS documentation-এর উদাহরণ key
DOC_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # scan-secrets: allow — AWS documentation-এর উদাহরণ
DOC_SIGNATURE = "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"


class PresignTest(unittest.TestCase):
    def test_matches_aws_documentation_example(self) -> None:
        url = ps.presign("examplebucket", "test.txt", "us-east-1", DOC_KEY_ID, DOC_SECRET,
                         datetime(2013, 5, 24, tzinfo=UTC), 86400, host="examplebucket.s3.amazonaws.com")
        self.assertTrue(url.endswith("&X-Amz-Signature=" + DOC_SIGNATURE), url)
        self.assertNotIn(DOC_SECRET, url)                                         # secret কখনো URL-এ নয়

    def test_session_token_and_key_encoding(self) -> None:
        url = ps.presign("b", "reports/Q1 2026+final.csv", "ap-south-1", "ASIAEXAMPLE", "s", datetime(2026, 10, 28,
                         tzinfo=UTC), 300, session_token="tok/en+=")  # scan-secrets: allow — নকল token
        self.assertIn("/reports/Q1%202026%2Bfinal.csv?", url)                       # space ও + encode, / নয়
        self.assertIn("X-Amz-Security-Token=tok%2Fen%2B%3D", url)
        self.assertIn("b.s3.ap-south-1.amazonaws.com", url)

    def test_expiry_bounds(self) -> None:
        for bad in (0, 604801):
            with self.assertRaises(ValueError):
                ps.presign("b", "k", "us-east-1", "A", "s", datetime(2026, 1, 1, tzinfo=UTC), bad)


class S3AuditTest(unittest.TestCase):
    def test_samples(self) -> None:
        pub = sa.audit_bucket(S / "lab08-public-site")
        self.assertEqual([lvl for lvl, _ in pub].count("CRITICAL"), 2)
        self.assertEqual([lvl for lvl, _ in sa.audit_bucket(S / "lab08-uploads")], ["WARN"])

    def test_fixes_and_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            b = Path(d, "b")
            shutil.copytree(S / "lab08-uploads", b)
            shutil.copy(S / "lifecycle-good.json", b / "lifecycle.json")
            self.assertEqual(sa.audit_bucket(b), [])                                # পুরো ঠিক
            vpce = {"Version": "2012-10-17", "Statement": [
                {"Sid": "VpceOnly", "Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "*",
                 "Condition": {"StringEquals": {"aws:SourceVpce": "vpce-1"}}},
                {"Sid": "Tls", "Effect": "Deny", "Principal": "*", "Action": "s3:*", "Resource": "*",
                 "Condition": {"Bool": {"aws:SecureTransport": "false"}}}]}
            (b / "policy.json").write_text(json.dumps({"Policy": json.dumps(vpce)}), encoding="utf-8")
            self.assertEqual(sa.audit_bucket(b), [])                                # condition-এ সীমিত — public নয়
            (b / "versioning.json").write_text("", encoding="utf-8")                  # CLI error → খালি file
            self.assertIn("never enabled", sa.audit_bucket(b)[0][1])

    def test_restrict_public_buckets_downgrades(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            b = Path(d, "b")
            shutil.copytree(S / "lab08-public-site", b)
            pab = {k: True for k in sa.PAB_KEYS}
            (b / "public-access-block.json").write_text(json.dumps({"PublicAccessBlockConfiguration": pab}),
                                                        encoding="utf-8")
            levels = [lvl for lvl, m in sa.audit_bucket(b) if m.startswith("policy PublicRead")]
            self.assertEqual(levels, ["WARN"])


if __name__ == "__main__":
    unittest.main()
