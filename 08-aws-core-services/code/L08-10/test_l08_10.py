"""Tests for r53_plan.py — চালানো: python3 -m unittest -v (হাতে তৈরি নমুনা, কোনো AWS call নেই)"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import r53_plan as rp  # noqa: E402

S = HERE / "sample"
CURRENT = json.loads((S / "current.json").read_text(encoding="utf-8"))
DESIRED = json.loads((S / "desired.json").read_text(encoding="utf-8"))


def actions(changes: list[dict]) -> list[tuple[str, str, str]]:
    return [(c["Action"], c["ResourceRecordSet"]["Name"], c["ResourceRecordSet"]["Type"]) for c in changes]


class Route53PlanTest(unittest.TestCase):
    def test_names(self) -> None:
        z = "example.com"
        self.assertEqual(rp.fqdn("@", z), "example.com.")
        self.assertEqual(rp.fqdn("app", z), "app.example.com.")
        self.assertEqual(rp.fqdn("App.Example.com", z), "app.example.com.")
        self.assertEqual(rp.fqdn("\\052.dev.example.com.", z), "*.dev.example.com.")   # Route 53-এর octal escape

    def test_sample_plan_only_changes(self) -> None:
        changes, errors, notes = rp.plan(CURRENT, DESIRED, "example.com", prune=False)
        self.assertEqual(errors, [])
        self.assertEqual(actions(changes), [("UPSERT", "app.example.com.", "A"),
                                            ("UPSERT", "_acme-check.example.com.", "TXT")])   # www ও *.dev অপরিবর্তিত
        self.assertEqual(len(notes), 1)
        self.assertIn("86400", notes[0])                                         # বড় TTL — আগে কমান
        alias = changes[0]["ResourceRecordSet"]
        self.assertNotIn("TTL", alias)
        self.assertTrue(alias["AliasTarget"]["DNSName"].endswith("."))

    def test_prune_never_touches_apex_ns_soa(self) -> None:
        changes, _, _ = rp.plan(CURRENT, DESIRED, "example.com", prune=True)
        self.assertEqual(actions(changes)[0], ("DELETE", "old.example.com.", "A"))     # DELETE আগে
        self.assertNotIn("NS", [t for _, _, t in actions(changes)])
        self.assertNotIn("SOA", [t for _, _, t in actions(changes)])

    def test_validation(self) -> None:
        bad = json.loads((S / "desired-bad.json").read_text(encoding="utf-8"))
        _, errors, _ = rp.plan(CURRENT, bad, "example.com", prune=False)
        self.assertEqual(len(errors), 3)
        self.assertTrue(any("apex" in e for e in errors))
        self.assertTrue(any("coexist" in e for e in errors))
        self.assertTrue(any("no TTL" in e for e in errors))
        # --prune-এ পুরোনো CNAME মুছে A বসানো বৈধ
        _, errors, _ = rp.plan(CURRENT, [bad[1]], "example.com", prune=True)
        self.assertEqual(errors, [])

    def test_idempotent(self) -> None:
        changes, _, _ = rp.plan(CURRENT, DESIRED, "example.com", prune=False)
        after = {"ResourceRecordSets": [r for r in CURRENT["ResourceRecordSets"]
                                        if r["Name"] != "app.example.com."] + [c["ResourceRecordSet"] for c in changes]}
        self.assertEqual(rp.plan(after, DESIRED, "example.com", prune=False)[0], [])   # প্রয়োগের পরে আর কিছু নয়


if __name__ == "__main__":
    unittest.main()
