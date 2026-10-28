"""Tests for sg_reach.py — চালানো: python3 -m unittest -v (হাতে তৈরি describe-* নমুনা, কোনো AWS call নেই)"""
from __future__ import annotations

import copy
import dataclasses
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sg_reach as sr  # noqa: E402

S = HERE / "sample"
GROUPS = {g["GroupId"]: g for g in json.loads((S / "security-groups.json").read_text(encoding="utf-8"))["SecurityGroups"]}
ACLS = json.loads((S / "network-acls.json").read_text(encoding="utf-8"))["NetworkAcls"]
ALB_TO_APP = sr.Flow("alb→app", "10.20.0.10", "10.20.16.5", 8000, src_sgs=["sg-alb"], src_subnet="subnet-pub-a",
                     dst_sgs=["sg-app"], dst_subnet="subnet-app-a")


def verdict(flow: sr.Flow, groups: dict = GROUPS, acls: list = ACLS) -> tuple[bool, str]:
    steps = sr.check(flow, groups, acls)
    return all(ok for ok, _ in steps), steps[-1][1]


class ReachTest(unittest.TestCase):
    def test_sample_flows_as_expected(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = sr.main(["check", str(S / "security-groups.json"), str(S / "network-acls.json"),
                          "--flows", str(S / "flows.json")])
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("6 flow(s), 0 unexpected", out.getvalue())

    def test_stateless_return_path(self) -> None:
        # ক্লাসিক ভুল: কাস্টম NACL-এ ফেরতের ephemeral port-এর inbound allow নেই
        acls = copy.deepcopy(ACLS)
        public = next(a for a in acls if a["NetworkAclId"] == "acl-default")
        public["Entries"] = [e for e in public["Entries"] if e["Egress"] or e["RuleNumber"] == 32767] + [
            {"RuleNumber": 100, "Protocol": "6", "RuleAction": "allow", "Egress": False, "CidrBlock": "0.0.0.0/0",
             "PortRange": {"From": 443, "To": 443}}]
        ok, last = verdict(ALB_TO_APP, acls=acls)
        self.assertFalse(ok)
        self.assertTrue(last.startswith("return: source NACL inbound on port 50000"), last)

    def test_same_subnet_skips_nacl(self) -> None:
        acls = copy.deepcopy(ACLS)
        for a in acls:
            a["Entries"] = [e for e in a["Entries"] if e["RuleNumber"] == 32767]       # সব deny
        flow = dataclasses.replace(ALB_TO_APP, src_subnet="subnet-app-a")
        self.assertTrue(verdict(flow, acls=acls)[0])                                # একই subnet: NACL প্রযোজ্য নয়

    def test_rule_order_and_protocol(self) -> None:
        acl = next(a for a in ACLS if a["NetworkAclId"] == "acl-app")
        self.assertEqual(sr.acl_decides(acl, False, "198.51.100.7", 22, "tcp"), (False, "acl-app rule 90 deny"))
        self.assertEqual(sr.acl_decides(acl, False, "10.20.0.10", 8000, "udp"), (False, "acl-app rule * deny"))
        flow = sr.Flow("udp", "10.20.0.10", "10.20.16.5", 8000, proto="udp", dst_sgs=["sg-app"])
        self.assertFalse(verdict(flow)[0])                                          # SG rule শুধু tcp

    def test_ipv6_and_sg_reference(self) -> None:
        self.assertIsNotNone(sr.sg_allows(GROUPS, ["sg-alb"], "IpPermissions", "2001:db8::1", [], 443, "tcp"))
        self.assertIsNone(sr.sg_allows(GROUPS, ["sg-alb"], "IpPermissions", "2001:db8::1", [], 80, "tcp"))
        self.assertEqual(sr.sg_allows(GROUPS, ["sg-db"], "IpPermissions", "10.9.9.9", ["sg-app"], 5432, "tcp"),
                         "sg-db ← sg-app")

    def test_audit(self) -> None:
        got = sr.audit(GROUPS)
        self.assertIn(("CRITICAL", "sg-app", "SSH (22) open to 0.0.0.0/0 — use SSM Session Manager or a "
                                             "source-restricted rule"), got)
        g = copy.deepcopy(GROUPS)
        g["sg-db"]["IpPermissions"].append({"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]})
        self.assertIn(("CRITICAL", "sg-db", "all traffic from 0.0.0.0/0"), sr.audit(g))


if __name__ == "__main__":
    unittest.main()
