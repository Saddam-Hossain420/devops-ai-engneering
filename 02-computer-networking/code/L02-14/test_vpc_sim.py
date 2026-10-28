"""Tests for vpc_sim.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import vpc_sim as vs  # noqa: E402

SAMPLE = HERE / "sample-vpcs.json"


class TraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = json.loads(SAMPLE.read_text(encoding="utf-8"))
        self.m = vs.Model(self.spec)

    def test_public_instance_to_internet(self) -> None:
        ok, hops = vs.trace(self.m, "web-1", "1.1.1.1")
        self.assertTrue(ok)
        self.assertIn("internet gateway", hops[-1])

    def test_private_via_nat(self) -> None:
        ok, hops = vs.trace(self.m, "api-2", "1.1.1.1")            # AZ b → NAT in AZ a
        self.assertTrue(ok)
        self.assertTrue(any("NAT gateway nat-a" in h and "AZ a" in h for h in hops))

    def test_data_tier_has_no_egress(self) -> None:
        ok, hops = vs.trace(self.m, "db-1", "1.1.1.1")
        self.assertFalse(ok)
        self.assertIn("no route", hops[-1])
        self.assertTrue(vs.trace(self.m, "db-1", "10.0.10.5")[0])  # VPC-র ভেতরে local route

    def test_peering_and_return_path(self) -> None:
        self.assertTrue(vs.trace(self.m, "api-1", "10.1.2.10")[0])  # tools-এ return route আছে
        ok, hops = vs.trace(self.m, "api-1", "10.1.3.10")           # metrics-এ নেই
        self.assertFalse(ok)
        self.assertIn("return path broken", hops[-1])

    def test_peering_not_transitive(self) -> None:
        spec = copy.deepcopy(self.spec)
        # shared-এর মাধ্যমে prod থেকে 172.16.0.0/16-এ যাওয়ার চেষ্টা
        spec["vpcs"]["prod"]["route_tables"]["private"].append({"dest": "172.16.0.0/16", "target": "pcx:prod-shared"})
        ok, hops = vs.trace(vs.Model(spec), "api-1", "172.16.5.5")
        self.assertFalse(ok)
        self.assertIn("NOT transitive", hops[-1])

    def test_private_instance_cannot_use_igw(self) -> None:
        spec = copy.deepcopy(self.spec)
        spec["instances"]["no-pub"] = {"subnet": "prod-public-b", "ip": "10.0.1.9"}
        ok, hops = vs.trace(vs.Model(spec), "no-pub", "1.1.1.1")
        self.assertFalse(ok)
        self.assertIn("no public IP", hops[-1])


class LintTest(unittest.TestCase):
    def test_sample(self) -> None:
        findings = vs.lint(vs.load(SAMPLE))
        text = "\n".join(findings)
        self.assertIn("ERROR shared peers with both dev and prod, whose CIDRs overlap", text)
        self.assertIn("NAT gateway nat-a serves subnets in AZs ['a', 'b']", text)
        self.assertEqual(len(findings), 2)

    def test_direct_overlap(self) -> None:
        spec = json.loads(SAMPLE.read_text(encoding="utf-8"))
        spec["peerings"]["prod-dev"] = ["prod", "dev"]
        self.assertTrue(any("ERROR peering prod-dev" in f for f in vs.lint(vs.Model(spec))))

    def test_detects_broken_designs(self) -> None:
        spec = json.loads(SAMPLE.read_text(encoding="utf-8"))
        prod = spec["vpcs"]["prod"]
        prod["subnets"]["bad"] = {"cidr": "10.9.0.0/24", "az": "a", "tier": "app", "route_table": "data"}
        prod["nat_gateways"]["nat-x"] = {"subnet": "prod-app-a"}
        prod["route_tables"]["data"].append({"dest": "0.0.0.0/0", "target": "nat:ghost"})
        spec["instances"]["db-1"]["public_ip"] = True
        text = "\n".join(vs.lint(vs.Model(spec)))
        self.assertIn("subnet bad 10.9.0.0/24 is outside prod", text)
        self.assertIn("nat-x sits in prod-app-a", text)
        self.assertIn("NAT gateway ghost does not exist", text)
        self.assertIn("instance db-1 has a public IP but its subnet has no route", text)

    def test_cli(self) -> None:
        self.assertEqual(vs.main(["trace", str(SAMPLE), "--from", "api-1", "--to", "1.1.1.1"]), 0)
        self.assertEqual(vs.main(["trace", str(SAMPLE), "--from", "db-1", "--to", "1.1.1.1"]), 1)
        self.assertEqual(vs.main(["trace", str(SAMPLE), "--from", "nobody", "--to", "1.1.1.1"]), 2)
        self.assertEqual(vs.main(["trace", str(SAMPLE), "--from", "api-1", "--to", "not-an-ip"]), 2)


if __name__ == "__main__":
    unittest.main()
