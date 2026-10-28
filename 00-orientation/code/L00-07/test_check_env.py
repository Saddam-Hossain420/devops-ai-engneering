"""Tests for check_env.py — চালানো: python3 -m unittest -v (এই folder থেকে)।

Test-গুলো আসল machine-এর উপর নির্ভর করে না: OS file-এর নমুনা text ব্যবহার করে।
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import check_env as ce  # noqa: E402

UBUNTU_OS_RELEASE = '''PRETTY_NAME="Ubuntu 24.04.1 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
ID=ubuntu
ID_LIKE=debian
'''
FEDORA_OS_RELEASE = 'NAME="Fedora Linux"\nID=fedora\nPRETTY_NAME="Fedora Linux 41 (Workstation Edition)"\n'
MEMINFO = "MemTotal:       16314064 kB\nMemFree:         1234567 kB\n"


class ParseTest(unittest.TestCase):
    def test_os_release(self) -> None:
        d = ce.parse_os_release(UBUNTU_OS_RELEASE + "# comment\n\n")
        self.assertEqual(d["ID"], "ubuntu")
        self.assertEqual(d["PRETTY_NAME"], "Ubuntu 24.04.1 LTS")

    def test_meminfo(self) -> None:
        self.assertEqual(ce.parse_meminfo_gb(MEMINFO), 15.6)
        self.assertIsNone(ce.parse_meminfo_gb("garbage"))

    def test_wsl_detection(self) -> None:
        self.assertTrue(ce.is_wsl("Linux version 5.15.167.4-microsoft-standard-WSL2"))
        self.assertFalse(ce.is_wsl("Linux version 6.8.0-45-generic (buildd@lcy02)"))


class OsCheckTest(unittest.TestCase):
    def test_ubuntu_pass(self) -> None:
        c = ce.check_os(ce.parse_os_release(UBUNTU_OS_RELEASE), "Linux")
        self.assertEqual(c.status, "PASS")

    def test_fedora_pass_with_note(self) -> None:
        c = ce.check_os(ce.parse_os_release(FEDORA_OS_RELEASE), "Linux")
        self.assertEqual(c.status, "PASS")
        self.assertIn("Fedora", c.detail)

    def test_other_linux_warn_and_windows_fail(self) -> None:
        self.assertEqual(ce.check_os({"ID": "arch"}, "Linux").status, "WARN")
        self.assertEqual(ce.check_os({}, "Windows").status, "FAIL")


class PythonAndToolsTest(unittest.TestCase):
    def test_python_version(self) -> None:
        self.assertEqual(ce.check_python((3, 12, 3), True)[0].status, "PASS")
        self.assertEqual(ce.check_python((3, 8, 10), False)[0].status, "FAIL")
        self.assertEqual(ce.check_python((3, 12, 3), False)[1].status, "INFO")

    def test_tools_with_fake_which(self) -> None:
        present = {"git", "curl", "docker"}
        checks = {c.name: c.status for c in ce.check_tools(lambda t: f"/usr/bin/{t}" if t in present else None)}
        self.assertEqual(checks["tool:git"], "PASS")
        self.assertEqual(checks["tool:jq"], "FAIL")       # required, missing
        self.assertEqual(checks["tool:docker"], "PASS")
        self.assertEqual(checks["tool:mtr"], "INFO")      # optional, missing

    def test_resources(self) -> None:
        statuses = [c.status for c in ce.check_resources(2.0, 1, 5.0)]
        self.assertEqual(statuses, ["WARN", "WARN", "WARN"])
        statuses = [c.status for c in ce.check_resources(16.0, 8, 100.0)]
        self.assertEqual(statuses, ["PASS", "PASS", "PASS"])


if __name__ == "__main__":
    unittest.main()
