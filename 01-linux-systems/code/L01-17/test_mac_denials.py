"""Tests for mac_denials.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mac_denials as md  # noqa: E402


def load(name: str) -> list[md.Denial]:
    return [d for d in map(md.parse_line, (HERE / name).read_text(encoding="utf-8").splitlines()) if d]


class AppArmorTest(unittest.TestCase):
    def test_parse_and_group(self) -> None:
        ds = load("sample-apparmor.log")
        self.assertEqual(len(ds), 3)
        self.assertEqual((ds[0].subject, ds[0].action, ds[0].target),
                         ("/usr/sbin/nginx", "open", "/srv/taskflow/static/app.js"))
        self.assertEqual(Counter(ds)[ds[0]], 2)          # দুটি একই denial এক group-এ
        self.assertEqual(ds[2].mode, "complain")
        self.assertIn("aa-logprof", md.suggest(ds[0]))


class SelinuxTest(unittest.TestCase):
    def test_parse(self) -> None:
        ds = load("sample-selinux.log")
        self.assertEqual(len(ds), 4)                     # SYSCALL লাইন বাদ
        self.assertEqual((ds[0].subject, ds[0].action, ds[0].target),
                         ("httpd_t", "read", "index.html (user_home_t)"))
        self.assertEqual(ds[3].mode, "permissive")
        self.assertEqual(ds[2].target, "port 8000 (soundd_port_t)")       # connect: dest=
        self.assertEqual(ds[3].target, "port 2222 (unreserved_port_t)")   # bind: src=

    def test_suggestions(self) -> None:
        ds = load("sample-selinux.log")
        self.assertIn("restorecon", md.suggest(ds[0]))
        self.assertIn("httpd_can_network_connect", md.suggest(ds[2]))
        self.assertIn("semanage port", md.suggest(ds[3]))

    def test_context_type(self) -> None:
        self.assertEqual(md.selinux_type("system_u:system_r:sshd_t:s0-s0:c0.c1023"), "sshd_t")


class CliTest(unittest.TestCase):
    def test_exit_codes(self) -> None:
        self.assertEqual(md.main([str(HERE / "sample-selinux.log")]), 1)
        self.assertEqual(md.main([str(HERE / "test_mac_denials.py")]), 0)   # কোনো denial নেই
        self.assertEqual(md.main([str(HERE / "missing.log")]), 2)


if __name__ == "__main__":
    unittest.main()
