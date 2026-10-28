"""Tests for ebs_audit.py ও fstab_lint.py — চালানো: python3 -m unittest -v (হাতে তৈরি নমুনা, কোনো AWS call নেই)"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ebs_audit as ea  # noqa: E402
import fstab_lint as fl  # noqa: E402

S = HERE / "sample"
VOLS = json.loads((S / "volumes.json").read_text(encoding="utf-8"))["Volumes"]
SNAPS = json.loads((S / "snapshots.json").read_text(encoding="utf-8"))["Snapshots"]
TODAY = date(2026, 10, 28)


class EbsAuditTest(unittest.TestCase):
    def test_sample(self) -> None:
        got = {(lvl, rid) for lvl, rid, _ in ea.audit(VOLS, SNAPS, TODAY, 90, False)}
        self.assertIn(("CRITICAL", "vol-data-old"), got)
        self.assertIn(("WARN", "vol-forgotten"), got)
        self.assertIn(("WARN", "account"), got)
        self.assertNotIn("snap-nightly", {rid for _, rid in got})                     # নতুন, encrypted, volume আছে
        self.assertNotIn("vol-root-app", {rid for _, rid in got})

    def test_ami_snapshot_not_called_orphan(self) -> None:
        msgs = [m for _, rid, m in ea.audit(VOLS, SNAPS, TODAY, 90, None) if rid == "snap-ami-base"]
        self.assertEqual(len(msgs), 1)
        self.assertIn("backs an AMI", msgs[0])

    def test_age_threshold_and_z_suffix(self) -> None:
        snap = copy.deepcopy(SNAPS[1])
        snap["StartTime"] = "2026-09-01T00:00:00Z"                                   # 'Z' — boto3/CLI দুই রূপই
        snap["Encrypted"] = True
        self.assertEqual(ea.audit([], [snap], TODAY, 90, None), [])                  # ৫৭ দিন — এখনো পুরোনো নয়
        self.assertEqual(len(ea.audit([], [snap], TODAY, 30, None)), 1)


class FstabLintTest(unittest.TestCase):
    def test_sample(self) -> None:
        got = [(n, lvl) for n, lvl, _ in fl.lint((S / "fstab").read_text(encoding="utf-8"))]
        self.assertEqual([lvl for n, lvl in got if n == 4], ["ERROR", "ERROR"])       # /dev/xvdf, nofail নেই
        self.assertIn((6, "ERROR"), got)                                             # soft
        self.assertNotIn(5, [n for n, _ in got])                                     # UUID + nofail ঠিক
        self.assertNotIn(2, [n for n, _ in got])                                     # root বাদ
        self.assertEqual([lvl for n, lvl in got if n == 7], ["INFO"])                # efs + tls + _netdev

    def test_good_lines(self) -> None:
        good = ("UUID=1111-2222 /data ext4 defaults,nofail 0 2\n"
                "fs-0123:/ /shared nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,"
                "noresvport,_netdev,nofail 0 0\n")
        self.assertEqual(fl.lint(good), [])

    def test_efs_type_needs_netdev_and_tls(self) -> None:
        got = fl.lint("fs-0abc:/ /x efs defaults,nofail 0 0\n")
        self.assertEqual(sorted(lvl for _, lvl, _ in got), ["ERROR", "WARN"])
        self.assertEqual(fl.lint("/dev/nvme1n1 /d ext4 defaults,nofail 0 2\n")[0][1], "ERROR")


if __name__ == "__main__":
    unittest.main()
