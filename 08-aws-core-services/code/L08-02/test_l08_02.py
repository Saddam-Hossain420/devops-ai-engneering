"""Tests for aws_config_audit.py ও inventory.py — চালানো: python3 -m unittest -v
boto3 লাগে না: inventory একটি নকল session দিয়ে পরীক্ষা হয় (API-র রূপ boto3 documentation অনুযায়ী, হাতে তৈরি)।"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import aws_config_audit as ca  # noqa: E402
import inventory as inv  # noqa: E402

S = HERE / "sample"


def load() -> tuple[dict, dict, set]:
    config, cred = ca.read_ini(S / "config"), ca.read_ini(S / "credentials")
    return ca.profiles_of(config), {s: dict(cred[s]) for s in cred.sections()}, ca.sso_sessions_of(config)


class ConfigAuditTest(unittest.TestCase):
    def test_sample_findings(self) -> None:
        got = {(f.level, f.profile, f.message.split(" ")[0]) for f in ca.audit(*load())}
        self.assertIn(("ERROR", "broken-chain", "source_profile"), got)
        self.assertIn(("ERROR", "half-sso", "SSO"), got)
        self.assertIn(("ERROR", "temp-without-token", "temporary"), got)
        self.assertIn(("WARN", "old-keys", "long-lived"), got)
        self.assertNotIn("learn-admin", {p for _, p, _ in got})                     # সম্পূর্ণ SSO profile পরিষ্কার

    def test_secrets_never_printed(self) -> None:
        text = " ".join(f.message for f in ca.audit(*load()))
        self.assertNotIn("not-a-real-secret", text)
        self.assertNotIn("AKIAEXAMPLE-LAB-0001", text)                            # key id-ও masked
        self.assertEqual(ca.mask("AKIAEXAMPLE-LAB-0001"), "AKIA…0001")

    def test_role_chain_loop(self) -> None:
        profiles = {"a": {"role_arn": "x", "source_profile": "b", "region": "r"},
                    "b": {"role_arn": "y", "source_profile": "a", "region": "r"}}
        self.assertTrue(any("loops" in f.message for f in ca.audit(profiles, {}, set())))

    def test_which_precedence(self) -> None:
        profiles, creds, _ = load()
        self.assertEqual(ca.which("deployer", {"AWS_ACCESS_KEY_ID": "AKIAX"}, profiles, creds),
                         "--profile deployer: assume-role")                       # --profile env-এর ওপরে
        self.assertTrue(ca.which(None, {"AWS_ACCESS_KEY_ID": "ASIAX", "AWS_PROFILE": "learn-admin"}, profiles, creds)
                        .startswith("environment variables: temporary-keys"))
        self.assertEqual(ca.which(None, {"AWS_PROFILE": "learn-admin"}, profiles, creds), "profile learn-admin: sso")


class FakePaginator:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self._pages = pages

    def paginate(self, **_: Any) -> list[dict[str, Any]]:
        return self._pages


class FakeClient:
    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.calls: list[str] = []

    def get_paginator(self, op: str) -> FakePaginator:
        self.calls.append(op)
        return FakePaginator(self.data.get(op, [{}]))

    def __getattr__(self, op: str) -> Any:
        if op.startswith(("describe_", "list_", "get_")):
            def call(**_: Any) -> Any:
                self.calls.append(op)
                return self.data.get(op, {})
            return call
        raise AttributeError(op)


class FakeSession:
    region_name = "ap-south-1"

    def __init__(self) -> None:
        self.clients: list[FakeClient] = []

    def client(self, name: str, region_name: str | None = None) -> FakeClient:
        data: dict[str, dict[str, Any]] = {
            "sts": {"get_caller_identity": {"Account": "111122223333",
                                            "Arn": "arn:aws:sts::111122223333:assumed-role/AWSReservedSSO_Admin_abc/ana"}},
            "ec2": {"describe_regions": {"Regions": [{"RegionName": "ap-south-1"}]},
                    "describe_instances": [{"Reservations": [{"Instances": [
                        {"InstanceId": "i-1", "State": {"Name": "running"}, "InstanceType": "t3.micro",
                         "Tags": [{"Key": "Project", "Value": "lab08"}]},
                        {"InstanceId": "i-old", "State": {"Name": "terminated"}}]}]},
                        {"Reservations": [{"Instances": [{"InstanceId": "i-2", "State": {"Name": "stopped"}}]}]}],
                    "describe_volumes": [{"Volumes": [{"VolumeId": "vol-1", "State": "available", "Size": 8}]}],
                    "describe_addresses": {"Addresses": [{"AllocationId": "eipalloc-1", "PublicIp": "203.0.113.5"}]},
                    "describe_nat_gateways": [{"NatGateways": [{"NatGatewayId": "nat-1", "State": "available"},
                                                               {"NatGatewayId": "nat-0", "State": "deleted"}]}]},
            "elbv2": {"describe_load_balancers": [{"LoadBalancers": []}]},
            "s3": {"list_buckets": {"Buckets": [{"Name": "lab08-bucket"}]}},
        }[name]
        c = FakeClient(data)
        self.clients.append(c)
        return c


class InventoryTest(unittest.TestCase):
    def test_collect_with_pagination_and_filters(self) -> None:
        session = FakeSession()
        data = inv.collect(session, None)
        ids = [(r["type"], r["id"], r["state"]) for r in data["resources"]]
        self.assertEqual(ids, [("ec2-instance", "i-1", "running"), ("ec2-instance", "i-2", "stopped"),   # দুই page
                               ("ebs-volume", "vol-1", "available"), ("elastic-ip", "eipalloc-1", "unassociated"),
                               ("nat-gateway", "nat-1", "available"), ("s3-bucket", "lab08-bucket", "exists")])
        self.assertEqual(data["caller_kind"], "assumed-role (IAM Identity Center)")
        self.assertEqual(data["resources"][0]["tags"], {"Project": "lab08"})

    def test_only_read_calls(self) -> None:
        session = FakeSession()
        inv.collect(session, ["ap-south-1"])
        calls = {c for client in session.clients for c in client.calls}
        self.assertTrue(all(c.startswith(("describe_", "list_", "get_")) for c in calls), calls)

    def test_arn_kind(self) -> None:
        self.assertEqual(inv.arn_kind("arn:aws:iam::111122223333:root"), "root")
        self.assertEqual(inv.arn_kind("arn:aws:iam::111122223333:user/ana"), "iam-user")
        self.assertEqual(inv.arn_kind("arn:aws:sts::111122223333:assumed-role/taskflow-deployer/s1"), "assumed-role")


if __name__ == "__main__":
    unittest.main()
