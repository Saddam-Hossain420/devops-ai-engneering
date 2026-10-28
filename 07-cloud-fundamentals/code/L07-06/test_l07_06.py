"""Tests for cost_estimate.py ও tag_audit.py — চালানো: python3 -m unittest -v (example-prices.json — আসল দাম নয়)"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cost_estimate as ce  # noqa: E402
import tag_audit as ta  # noqa: E402

PRICES = json.loads((HERE / "example-prices.json").read_text(encoding="utf-8"))
ARCH = json.loads((HERE / "taskflow-arch.json").read_text(encoding="utf-8"))


def total(arch: dict, dev_hours: float | None = None) -> float:
    return round(sum(ln.cost for ln in ce.lines_for(arch, PRICES, dev_hours)), 2)


class CostTest(unittest.TestCase):
    def test_sample_total_and_lines(self) -> None:
        self.assertEqual(total(ARCH), 717.25)
        single = {"resources": [{"name": "vm", "type": "small-vm"}]}
        self.assertAlmostEqual(total(single), 730 * 0.02)                         # ৭৩০ ঘণ্টা/মাস

    def test_scheduling_changes_compute_not_storage(self) -> None:
        dev = {"resources": [{"name": "d", "env": "dev", "type": "medium-vm", "storage_gb": 100}]}
        lines = {ln.item: ln.cost for ln in ce.lines_for(dev, PRICES, dev_hours=12 * 22)}
        self.assertAlmostEqual(lines["compute medium-vm"], 264 * 0.08)
        self.assertAlmostEqual(lines["storage_gb"], 100 * 0.10)                   # বন্ধ থাকলেও disk-এর বিল
        prod = {"resources": [{"name": "p", "env": "prod", "type": "medium-vm"}]}
        self.assertEqual(total(prod, dev_hours=264), total(prod))                 # prod schedule হয় না

    def test_scheduled_sample_and_unknown_type(self) -> None:
        self.assertLess(total(ARCH, 264), total(ARCH) * 0.7)
        with self.assertRaisesRegex(KeyError, "no price"):
            ce.lines_for({"resources": [{"name": "x", "type": "quantum-vm"}]}, PRICES)

    def test_budget_alerts_and_warning_shown(self) -> None:
        self.assertEqual(ce.budget_alerts(100.0), [("50%", 50.0), ("80%", 80.0), ("100%", 100.0), ("120%", 120.0)])
        out = io.StringIO()
        with redirect_stdout(out):
            ce.main([str(HERE / "taskflow-arch.json"), "--prices", str(HERE / "example-prices.json")])
        self.assertIn("EXAMPLE PRICES ONLY", out.getvalue())                       # সতর্কতা সবসময় দেখায়


class TagAuditTest(unittest.TestCase):
    def test_sample_findings(self) -> None:
        inv = json.loads((HERE / "inventory.json").read_text(encoding="utf-8"))
        findings = ta.audit(inv, date(2026, 10, 28), ta.DEFAULT_REQUIRED, 90)
        kinds = sorted((f.kind, f.id) for f in findings)
        self.assertEqual(kinds, [
            ("bad-expires", "snap-before-migration"), ("expired", "i-demo-ana"),
            ("idle-public-ip", "eip-old-demo"), ("missing-tags", "i-mystery"), ("missing-tags", "vol-orphan-2025"),
            ("old-snapshot", "snap-before-migration"), ("stopped-instance-volume", "vol-loadtest-7"),
            ("unattached-volume", "vol-orphan-2025")])

    def test_expires_boundary_and_tag_case(self) -> None:
        inv = [{"id": "a", "type": "instance", "tags": {"Owner": "x", "ENV": "dev", "Cost-Center": "c",
                                                         "expires": "2026-10-28"}}]
        self.assertEqual(ta.audit(inv, date(2026, 10, 28), ta.DEFAULT_REQUIRED, 90), [])   # আজকের দিনে এখনো বৈধ
        self.assertEqual(ta.audit(inv, date(2026, 10, 29), ta.DEFAULT_REQUIRED, 90)[0].kind, "expired")


if __name__ == "__main__":
    unittest.main()
