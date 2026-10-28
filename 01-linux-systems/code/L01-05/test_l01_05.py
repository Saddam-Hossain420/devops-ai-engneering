"""Tests for acl_check.py and sudoers_audit.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import acl_check as ac  # noqa: E402
import sudoers_audit as sa  # noqa: E402


class AclTest(unittest.TestCase):
    def setUp(self) -> None:
        self.acl = ac.parse_getfacl((HERE / "sample-getfacl.txt").read_text(encoding="utf-8"))

    def test_parse(self) -> None:
        self.assertEqual((self.acl.owner, self.acl.group), ("sami", "developers"))
        self.assertEqual(self.acl.users, {"alice": 6, "bob": 4})
        self.assertEqual(self.acl.mask, 4)

    def test_mask_limits_named_user(self) -> None:
        ok, why = ac.decide(self.acl, "alice", {"alice"}, "w")
        self.assertFalse(ok)                      # entry rw- কিন্তু mask r--
        self.assertIn("effective r--", why)
        self.assertTrue(ac.decide(self.acl, "alice", {"alice"}, "r")[0])

    def test_owner_not_masked(self) -> None:
        self.assertTrue(ac.decide(self.acl, "sami", {"sami"}, "w")[0])

    def test_group_and_other(self) -> None:
        self.assertTrue(ac.decide(self.acl, "carol", {"carol", "auditors"}, "r")[0])
        self.assertFalse(ac.decide(self.acl, "carol", {"carol", "auditors"}, "w")[0])
        self.assertFalse(ac.decide(self.acl, "eve", {"eve"}, "r")[0])   # other ---

    def test_named_user_beats_group(self) -> None:
        # bob developers group-এ থাকলেও named user entry আগে মেলে
        ok, why = ac.decide(self.acl, "bob", {"bob", "developers"}, "r")
        self.assertTrue(ok)
        self.assertIn("named user", why)

    def test_errors(self) -> None:
        with self.assertRaises(ValueError):
            ac.parse_getfacl("user::rw-\n")       # no owner header
        with self.assertRaises(ValueError):
            ac.perm_bits("rwz")


class SudoersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.findings = sa.audit((HERE / "sample-sudoers.txt").read_text(encoding="utf-8"))
        self.msgs = [(f.severity, f.message) for f in self.findings]

    def test_critical_first(self) -> None:
        self.assertEqual(self.findings[0].severity, "CRITICAL")
        self.assertIn("contractor", self.findings[0].message)

    def test_expected_findings(self) -> None:
        text = "\n".join(f"{s} {m}" for s, m in self.msgs)
        self.assertIn("HIGH %sudo: full root via ALL", text)
        self.assertIn("HIGH support: less can spawn a shell", text)
        self.assertIn("HIGH support: wildcard in '/usr/bin/less /var/log/*'", text)
        self.assertIn("MEDIUM backup: command without absolute path: tar", text)
        self.assertIn("HIGH backup: tar can spawn a shell", text)
        self.assertIn("HIGH backup: find can spawn a shell", text)
        self.assertIn("HIGH env_keep includes a library/loader variable", text)
        self.assertIn("HIGH deploy: systemctl can spawn a shell", text)

    def test_continuation_line_number(self) -> None:
        # backup rule starts on line 21 and continues on 22 — findings point to the start
        backup = [f for f in self.findings if "backup:" in f.message]
        self.assertTrue(backup and all(f.line == 21 for f in backup))

    def test_shell_escape_reported_once_per_line(self) -> None:
        deploy_escape = [f for f in self.findings if f.message.startswith("deploy: systemctl")]
        self.assertEqual(len(deploy_escape), 1)

    def test_clean_file(self) -> None:
        clean = "Defaults env_reset\ndeploy ALL=(root) /usr/local/bin/deploy-taskflow\n"
        self.assertEqual(sa.audit(clean), [])


if __name__ == "__main__":
    unittest.main()
