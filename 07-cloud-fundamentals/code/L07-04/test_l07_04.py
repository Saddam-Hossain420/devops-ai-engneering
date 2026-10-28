"""Tests for subnet_plan.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import ipaddress
import itertools
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import subnet_plan as sp  # noqa: E402


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


class PlanTest(unittest.TestCase):
    def test_sample_plan_is_valid(self) -> None:
        spec = load("taskflow-vpc.json")
        subnets, _ = sp.plan(spec)
        nets = [ipaddress.ip_network(s.cidr) for s in subnets]
        vpc = ipaddress.ip_network(spec["vpc"])
        self.assertEqual(len(subnets), 9)                                    # ৩ tier × ৩ AZ
        self.assertTrue(all(n.subnet_of(vpc) for n in nets))
        for a, b in itertools.combinations(nets, 2):
            self.assertFalse(a.overlaps(b), f"{a} overlaps {b}")
        for tier in spec["tiers"]:
            usable = [s.usable for s in subnets if s.tier == tier["name"]]
            self.assertTrue(all(u >= tier["hosts"] for u in usable))          # reserved বাদ দিয়েও যথেষ্ট
            self.assertEqual(len(set(usable)), 1)                            # প্রতিটি AZ-এ একই আকার

    def test_prefix_accounts_for_reserved(self) -> None:
        self.assertEqual(sp.prefix_for(59, 5), 26)        # ৬৪ - ৫ = ৫৯ ঠিক আঁটে
        self.assertEqual(sp.prefix_for(60, 5), 25)        # ৬০ + ৫ = ৬৫ → /25
        self.assertEqual(sp.prefix_for(2, 5), 28)         # ক্ষুদ্রতম /28

    def test_errors(self) -> None:
        with self.assertRaisesRegex(sp.PlanError, "overlaps office-vpn"):
            sp.plan(load("conflict-vpc.json"))
        with self.assertRaisesRegex(sp.PlanError, "no room left"):
            sp.plan(load("tiny-vpc.json"))
        with self.assertRaisesRegex(sp.PlanError, "not an RFC 1918"):
            sp.plan({"vpc": "8.8.0.0/16", "azs": ["a"], "tiers": []})

    def test_nat_needs_public_subnet(self) -> None:
        _, notes = sp.plan({"vpc": "10.9.0.0/16", "azs": ["a"], "tiers": [{"name": "app", "type": "private", "hosts": 10}]})
        self.assertTrue(any("NAT gateway" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
