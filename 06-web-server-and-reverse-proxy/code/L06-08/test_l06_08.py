"""Tests for harden_audit.py — চালানো: python3 -m unittest -v (নমুনা tree, যেকোনো OS)"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harden_audit as ha  # noqa: E402

SAMPLE = HERE / "sample-root"


def by_item(findings: list[ha.Finding]) -> dict[str, ha.Finding]:
    return {f.item: f for f in findings}


class SshdTest(unittest.TestCase):
    def test_first_value_wins_through_include(self) -> None:
        eff = ha.sshd_effective(SAMPLE)
        self.assertEqual(eff["passwordauthentication"], ("yes", "etc/ssh/sshd_config.d/50-cloud-init.conf:2"))
        self.assertEqual(eff["permitrootlogin"][0], "no")
        f = by_item(ha.audit_sshd(SAMPLE))
        self.assertEqual(f["passwordauthentication"].status, ha.CRITICAL)
        self.assertEqual(f["x11forwarding"].status, ha.WARNING)
        self.assertIn("built-in default", f["maxauthtries"].detail)

    def test_match_block_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "etc/ssh").mkdir(parents=True)
            (root / "etc/ssh/sshd_config").write_text(
                "PasswordAuthentication no\nMatch User deploy\n    PasswordAuthentication yes\n", encoding="utf-8")
            f = by_item(ha.audit_sshd(root))
            self.assertEqual(f["passwordauthentication"].status, ha.OK)              # Match-এর ভেতরেরটা global নয়
            self.assertEqual(f["permitrootlogin"].detail, "prohibit-password  ← built-in default")


class OtherAreasTest(unittest.TestCase):
    def test_sysctl(self) -> None:
        f = by_item(ha.audit_sysctl(SAMPLE, live=False))
        self.assertEqual(f["net.ipv4.ip_forward"].status, ha.WARNING)
        self.assertIn("not set", f["kernel.dmesg_restrict"].detail)
        self.assertEqual(f["net.ipv4.tcp_syncookies"].status, ha.OK)

    def test_ports(self) -> None:
        f = by_item(ha.audit_ports((SAMPLE / "ss-ltnH.txt").read_text(encoding="utf-8")))
        self.assertEqual(f["0.0.0.0:5432"].status, ha.CRITICAL)                       # database সবার জন্য খোলা
        self.assertEqual(f["[::]:9100"].status, ha.WARNING)
        self.assertEqual(f["127.0.0.1:8000"].status, ha.OK)
        self.assertEqual(f["127.0.0.53%lo:53"].status, ha.OK)

    def test_users_updates_nginx(self) -> None:
        self.assertIn("backup2", ha.audit_users(SAMPLE)[0].detail)
        self.assertEqual(ha.audit_updates(SAMPLE)[0].status, ha.OK)
        nginx = by_item(ha.audit_nginx(SAMPLE))
        self.assertEqual(nginx["server_tokens"].status, ha.WARNING)                   # comment-করা লাইন গোনা নয়

    def test_cli_exit_is_worst(self) -> None:
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ha.main(["--root", str(SAMPLE)]), ha.CRITICAL)


if __name__ == "__main__":
    unittest.main()
