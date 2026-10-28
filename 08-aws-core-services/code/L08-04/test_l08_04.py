"""Tests for vpc_audit.py — চালানো: python3 -m unittest -v (হাতে তৈরি describe-* নমুনা, কোনো AWS call নেই)"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import vpc_audit as va  # noqa: E402
import vpc_commands as vc  # noqa: E402

DATA = va.merge([json.loads(p.read_text(encoding="utf-8")) for p in sorted((HERE / "sample").glob("*.json"))])


def kinds(data: dict) -> dict[str, str]:
    return {v.id: v.kind for v in va.audit(data)[0]}


def messages(data: dict, level: str) -> list[str]:
    return [f"{i}: {m}" for lvl, i, m in va.audit(data)[1] if lvl == level]


class VpcAuditTest(unittest.TestCase):
    def test_sample_classification(self) -> None:
        self.assertEqual(kinds(DATA), {"subnet-pub-a": "public", "subnet-pub-b": "public", "subnet-app-a": "private",
                                       "subnet-app-b": "private", "subnet-data-a": "isolated",
                                       "subnet-legacy": "isolated"})
        self.assertEqual(len(messages(DATA, va.CRIT)), 1)
        self.assertEqual(len(messages(DATA, va.WARN)), 3)

    def test_nat_in_private_subnet(self) -> None:
        d = copy.deepcopy(DATA)
        d["NatGateways"][0]["SubnetId"] = "subnet-app-a"                     # NAT ভুল subnet-এ
        self.assertTrue(any("nat-a: public NAT gateway sits in private subnet" in m for m in messages(d, va.CRIT)))

    def test_main_table_with_internet_route(self) -> None:
        d = copy.deepcopy(DATA)
        main = next(t for t in d["RouteTables"] if t["RouteTableId"] == "rtb-main")
        main["Routes"].append({"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-0lab", "State": "active"})
        self.assertEqual(kinds(d)["subnet-data-a"], "public")               # নাম "data", কিন্তু এখন public
        self.assertTrue(any("MAIN route table has an internet route" in m for m in messages(d, va.CRIT)))

    def test_detached_igw_and_dead_nat(self) -> None:
        d = copy.deepcopy(DATA)
        d["InternetGateways"][0]["Attachments"] = []
        d["NatGateways"][0]["State"] = "failed"
        crit = " | ".join(messages(d, va.CRIT))
        self.assertIn("not attached to vpc-0lab", crit)
        self.assertIn("default route via nat-a, which is failed", crit)

    def test_classify_targets(self) -> None:
        self.assertEqual(va.classify(None), ("isolated", "no default route"))
        self.assertEqual(va.classify({"DestinationIpv6CidrBlock": "::/0", "GatewayId": "igw-1"})[0], "public")
        self.assertEqual(va.classify({"TransitGatewayId": "tgw-1"})[0], "private")
        self.assertEqual(va.classify({"GatewayId": "vgw-1"})[0], "isolated")    # VPN gateway-তে internet নয়
        table = {"Routes": [{"DestinationIpv6CidrBlock": "::/0", "GatewayId": "igw-1", "State": "active"}]}
        self.assertEqual(va.default_route(table)["GatewayId"], "igw-1")


PLAN = [{"tier": "public", "type": "public", "az": "a", "cidr": "10.20.2.0/26"},
        {"tier": "public", "type": "public", "az": "b", "cidr": "10.20.2.64/26"},
        {"tier": "app", "type": "private", "az": "a", "cidr": "10.20.0.0/24"},
        {"tier": "app", "type": "private", "az": "b", "cidr": "10.20.1.0/24"},
        {"tier": "data", "type": "isolated", "az": "a", "cidr": "10.20.3.0/24"}]


class VpcCommandsTest(unittest.TestCase):
    def test_every_create_is_tagged(self) -> None:

        text = vc.script(PLAN, "10.20.0.0/16", "ap-south-1", "lab08", "per-az")
        creates = [ln for ln in text.splitlines() if " create-" in ln and "create-route " not in ln
                   or "allocate-address" in ln]
        self.assertGreater(len(creates), 8)
        for ln in creates:
            self.assertIn("Key=Project,Value=lab08", ln)

    def test_nat_modes(self) -> None:

        count = {m: vc.script(PLAN, "10.20.0.0/16", "ap-south-1", "lab08", m).count("create-nat-gateway")
                 for m in ("none", "single", "per-az")}
        self.assertEqual(count, {"none": 0, "single": 1, "per-az": 2})
        text = vc.script(PLAN, "10.20.0.0/16", "ap-south-1", "lab08", "per-az")
        self.assertIn('--route-table-id "$RT_APP_B" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT_B"', text)
        data_rt = [ln for ln in text.splitlines() if "RT_DATA_A" in ln and "create-route " in ln]
        self.assertEqual(data_rt, [])                                       # isolated-এ default route নেই

    def test_rejects_bad_plans(self) -> None:

        with self.assertRaisesRegex(ValueError, "outside"):
            vc.script(PLAN, "10.30.0.0/16", "ap-south-1", "lab08", "none")
        with self.assertRaisesRegex(ValueError, "needs a public subnet"):
            vc.script(PLAN[2:], "10.20.0.0/16", "ap-south-1", "lab08", "single")
        with self.assertRaisesRegex(ValueError, "AZ b"):
            vc.script([PLAN[0]] + PLAN[2:], "10.20.0.0/16", "ap-south-1", "lab08", "per-az")


if __name__ == "__main__":
    unittest.main()
