"""Tests for perm_tool.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import perm_tool as pt  # noqa: E402


class ModeTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        for octal, sym in [("640", "rw-r-----"), ("755", "rwxr-xr-x"), ("4755", "rwsr-xr-x"),
                           ("2770", "rwxrws---"), ("1777", "rwxrwxrwt"), ("4644", "rwSr--r--")]:
            mode = pt.parse_mode(octal)
            self.assertEqual(pt.to_symbolic(mode), sym, octal)
            self.assertEqual(pt.parse_mode(sym), mode, sym)

    def test_ls_style_and_invalid(self) -> None:
        self.assertEqual(pt.parse_mode("-rw-r--r--"), 0o644)
        for bad in ("888", "rwxrwx", "rwzr--r--", "12345"):
            with self.assertRaises(ValueError, msg=bad):
                pt.parse_mode(bad)

    def test_umask(self) -> None:
        self.assertEqual(pt.apply_umask(0o022), (0o644, 0o755))
        self.assertEqual(pt.apply_umask(0o027), (0o640, 0o750))
        self.assertEqual(pt.apply_umask(0o077), (0o600, 0o700))


class AccessTest(unittest.TestCase):
    def test_owner_class_wins_even_if_less(self) -> None:
        # mode 0047: owner কিছুই পারে না, other সব পারে — owner তবু DENIED
        ok, why = pt.can_access(1000, {1000}, 1000, 1000, 0o047, "r")
        self.assertFalse(ok)
        self.assertIn("owner", why)
        self.assertTrue(pt.can_access(2000, {2000}, 1000, 1000, 0o047, "r")[0])

    def test_group_membership(self) -> None:
        # /etc/nginx-style: root:www-data 640
        self.assertTrue(pt.can_access(1001, {1001, 33}, 0, 33, 0o640, "r")[0])
        self.assertFalse(pt.can_access(1001, {1001, 33}, 0, 33, 0o640, "w")[0])
        self.assertFalse(pt.can_access(1002, {1002}, 0, 33, 0o640, "r")[0])

    def test_root(self) -> None:
        self.assertTrue(pt.can_access(0, {0}, 1000, 1000, 0o000, "w")[0])
        self.assertFalse(pt.can_access(0, {0}, 1000, 1000, 0o644, "x")[0])
        self.assertTrue(pt.can_access(0, {0}, 1000, 1000, 0o744, "x")[0])


class PasswdTest(unittest.TestCase):
    def test_login_users(self) -> None:
        users = pt.parse_passwd((HERE / "sample-passwd.txt").read_text(encoding="utf-8"))
        self.assertEqual(len(users), 11)
        self.assertEqual([u.name for u in pt.login_users(users)], ["root", "postgres", "sami", "deploy"])
        with self.assertRaises(ValueError):
            pt.parse_passwd("broken:line")


@unittest.skipUnless(os.name == "posix", "chmod semantics need a POSIX filesystem")
class AuditTest(unittest.TestCase):
    def test_audit_finds_world_writable_and_setuid(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "ok.txt").write_text("x")
            ww = root / "open.txt"
            ww.write_text("x")
            ww.chmod(0o666)
            su = root / "tool"
            su.write_text("x")
            su.chmod(0o4755)
            tmp = root / "shared"
            tmp.mkdir()
            tmp.chmod(0o1777)  # sticky → reported নয়
            findings = pt.audit(root)
        self.assertEqual(len(findings), 2)
        self.assertTrue(any("WORLD-WRITABLE" in f and "open.txt" in f for f in findings))
        self.assertTrue(any("SETUID" in f and "tool" in f for f in findings))


if __name__ == "__main__":
    unittest.main()
