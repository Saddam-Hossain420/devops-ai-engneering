"""Tests for virt_probe.py — চালানো: python3 -m unittest -v (নমুনা DMI tree, যেকোনো OS)"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import virt_probe as vp  # noqa: E402


def fake_root(d: str, vendor: str, product: str, hypervisor_flag: bool) -> Path:
    root = Path(d)
    (root / "sys/class/dmi/id").mkdir(parents=True)
    (root / "sys/class/dmi/id/sys_vendor").write_text(vendor + "\n")
    (root / "sys/class/dmi/id/product_name").write_text(product + "\n")
    (root / "proc").mkdir()
    flags = "fpu vme sse2" + (" hypervisor" if hypervisor_flag else "")
    (root / "proc/cpuinfo").write_text(f"processor\t: 0\nflags\t\t: {flags}\n")
    return root


class ClassifyTest(unittest.TestCase):
    def test_signatures(self) -> None:
        cases = {("QEMU", "Standard PC (Q35 + ICH9, 2009)"): "kvm", ("Amazon EC2", "m7i.large"): "amazon",
                 ("Google", "Google Compute Engine"): "google", ("innotek GmbH", "VirtualBox"): "oracle",
                 ("VMware, Inc.", "VMware Virtual Platform"): "vmware",
                 ("Microsoft Corporation", "Virtual Machine"): "microsoft",
                 ("Microsoft Corporation", "Surface Laptop 5"): None, ("HP", "HP EliteBook 845"): None}
        for (vendor, product), want in cases.items():
            with self.subTest(vendor=vendor):
                self.assertEqual(vp.classify(vendor, product), want)


class LinuxProbeTest(unittest.TestCase):
    def test_vm_from_dmi_and_flag(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = vp.probe_linux(fake_root(d, "QEMU", "Standard PC (Q35 + ICH9, 2009)", True))
        self.assertEqual((p.virtualized, p.hypervisor), (True, "kvm"))

    def test_flag_only_and_physical(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = vp.probe_linux(fake_root(d, "Some Vendor", "Custom Board", True))
        self.assertEqual((p.virtualized, p.hypervisor), (True, "unknown (hypervisor flag set)"))
        with tempfile.TemporaryDirectory() as d:
            p = vp.probe_linux(fake_root(d, "Dell Inc.", "PowerEdge R650", False))
        self.assertIs(p.virtualized, False)

    def test_no_evidence_is_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(vp.probe_linux(Path(d)).virtualized)


class NumbersTest(unittest.TestCase):
    def test_overcommit(self) -> None:
        r = vp.overcommit(32, 160, 256, 300)
        self.assertEqual((r["vcpu_per_pcpu"], r["memory_overcommit"], len(r["notes"])), (5.0, 1.17, 2))
        self.assertEqual(vp.overcommit(32, 64, 256, 128)["notes"], [])

    def test_steal(self) -> None:
        before = "cpu  1000 0 500 8000 100 0 0 0 0 0"
        after = "cpu  1300 0 600 8400 100 0 0 200 0 0"
        r = vp.steal_percent(before, after)
        self.assertEqual((r["steal"], r["user"], r["idle"]), (20.0, 30.0, 40.0))

    def test_cli_json(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            vp.main(["overcommit", "--host-cores", "8", "--vcpus", "8", "--host-ram-gb", "32", "--vm-ram-gb", "16"])
        self.assertEqual(json.loads(out.getvalue())["vcpu_per_pcpu"], 1.0)


if __name__ == "__main__":
    unittest.main()
