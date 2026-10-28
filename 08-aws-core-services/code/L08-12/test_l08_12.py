"""Tests for cleanup_plan.py ও ce_report.py — চালানো: python3 -m unittest -v
তৈরি করা cleanup script একটি নকল `aws` (bash function, প্রতিটি call log করে) দিয়ে আসলে চালানো হয় — কোনো AWS call নেই।"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ce_report as cr  # noqa: E402
import cleanup_plan as cp  # noqa: E402

S = HERE / "sample"
TAGGED = json.loads((S / "tagged.json").read_text(encoding="utf-8"))
BASH = shutil.which("bash")                    # পূর্ণ path — Windows-এ শুধু "bash" WSL চালাতে পারে
FAKE_AWS = r"""
aws() {
  echo "$*" >> "$AWS_LOG"
  case "$1 $2" in
    "sts get-caller-identity") echo "$FAKE_ACCOUNT" ;;
    "ec2 describe-internet-gateways") echo vpc-0lab ;;
    "ec2 describe-route-tables") echo 0 ;;
    "ec2 describe-security-group-rules") case "$*" in *'!IsEgress'*) echo sgr-in ;; *) echo sgr-out ;; esac ;;
    "s3api list-object-versions") echo '{"Objects": null, "Quiet": true}' ;;
    "ec2 describe-volumes"|"ec2 delete-volume") [ -z "$FAKE_VOLUME_GONE" ] || return 254 ;;   # আগেই মুছে গেছে
  esac
}
export -f aws
"""


def script() -> str:
    return cp.build(TAGGED, "Project=lab08", "111122223333", "ap-south-1")[0]


@unittest.skipUnless(BASH, "bash not found")
class CleanupScriptRunTest(unittest.TestCase):
    def run_script(self, account: str, execute: bool, volume_gone: bool = False) -> tuple[int, str, list[str]]:
        with tempfile.TemporaryDirectory() as d:
            sh, log = Path(d, "cleanup.sh"), Path(d, "aws.log")
            sh.write_text(script(), encoding="utf-8", newline="\n")
            log.touch()
            env_cmd = (f"export AWS_LOG='{log.as_posix()}' FAKE_ACCOUNT={account} EXECUTE={'yes' if execute else 'no'}"
                       f" FAKE_VOLUME_GONE={'1' if volume_gone else ''}")
            p = subprocess.run([BASH, "-c", f"{FAKE_AWS}\n{env_cmd}\nbash '{sh.as_posix()}'"],
                               capture_output=True, text=True, timeout=60)
            calls = log.read_text(encoding="utf-8").splitlines()
        return p.returncode, p.stdout + p.stderr, calls

    def test_dry_run_changes_nothing(self) -> None:
        rc, out, calls = self.run_script("111122223333", execute=False)
        self.assertEqual(rc, 0, out)
        mutating = [c for c in calls if c.split()[1].startswith(("delete", "terminate", "release", "revoke", "detach"))]
        self.assertEqual(mutating, [])                                           # শুধু describe/list/sts
        self.assertIn("DRY-RUN: aws ec2 delete-vpc --vpc-id vpc-0lab", out)

    def test_wrong_account_refused(self) -> None:
        rc, out, calls = self.run_script("999999999999", execute=True)
        self.assertEqual(rc, 2)
        self.assertIn("refusing", out)
        self.assertEqual(calls, ["sts get-caller-identity --query Account --output text"])

    def test_execute_order(self) -> None:
        rc, out, calls = self.run_script("111122223333", execute=True)
        self.assertEqual(rc, 0, out)
        verbs = [" ".join(c.split()[:2]) for c in calls]
        first = {v: verbs.index(v) for v in reversed(verbs)}
        order = ["elbv2 delete-load-balancer", "ec2 terminate-instances", "ec2 delete-nat-gateway",
                 "ec2 release-address", "ec2 revoke-security-group-ingress", "ec2 delete-security-group",
                 "ec2 detach-internet-gateway", "ec2 delete-subnet", "ec2 delete-route-table", "ec2 delete-vpc",
                 "s3api delete-bucket", "logs delete-log-group"]
        self.assertEqual(sorted(order, key=first.get), order)                    # নির্ভরতার ক্রম
        last_revoke = max(i for i, v in enumerate(verbs) if v.startswith("ec2 revoke"))
        self.assertLess(last_revoke, verbs.index("ec2 delete-security-group"))   # সব revoke আগে

    def test_volume_already_gone_does_not_abort(self) -> None:
        rc, out, calls = self.run_script("111122223333", execute=True, volume_gone=True)
        self.assertEqual(rc, 0, out)
        self.assertIn("skip vol-app-a: not found (deleted with its instance)", out)
        self.assertNotIn("ec2 delete-volume --volume-id vol-app-a", calls)
        self.assertIn("logs delete-log-group --log-group-name /lab08/taskflow", calls)   # বাকিটা চলেছে


class CleanupPlanTest(unittest.TestCase):
    def test_guards(self) -> None:
        for tag in ("Project=prod", "Project=Production", "Project"):
            with self.assertRaises(ValueError):
                cp.build(TAGGED, tag, "111122223333", "ap-south-1")
        with self.assertRaisesRegex(ValueError, "does not carry"):
            cp.build(TAGGED, "Project=other-lab", "111122223333", "ap-south-1")
        with self.assertRaisesRegex(ValueError, "outside"):
            cp.build(TAGGED, "Project=lab08", "111122223333", "us-east-1")

    def test_arn_parsing_and_manual(self) -> None:
        self.assertEqual(cp.parse_arn("arn:aws:ec2:ap-south-1::snapshot/snap-1").kind, "snapshot")   # account নেই
        self.assertEqual(cp.parse_arn("arn:aws:logs:ap-south-1:1:log-group:/lab08/x:*").id, "/lab08/x")
        self.assertEqual(cp.parse_arn("arn:aws:cloudwatch:ap-south-1:1:alarm:lab08-5xx").id, "lab08-5xx")
        _, manual = cp.build(TAGGED, "Project=lab08", "111122223333", "ap-south-1")
        self.assertEqual(manual, ["arn:aws:ssm:ap-south-1:111122223333:parameter/lab08/db-password"])


class CeReportTest(unittest.TestCase):
    def test_service_and_untagged(self) -> None:
        svc = cr.report(json.loads((S / "by-service.json").read_text(encoding="utf-8")))
        self.assertEqual(svc[0], "period 2026-10-01: total 21.77 USD")
        self.assertIn("EC2 - Other  (+717%", svc[1])
        self.assertTrue(any("(new)" in line for line in svc))
        tag = cr.report(json.loads((S / "by-project.json").read_text(encoding="utf-8")))
        self.assertTrue(tag[-1].startswith("untagged: 8.37 USD = 38%"))


if __name__ == "__main__":
    unittest.main()
