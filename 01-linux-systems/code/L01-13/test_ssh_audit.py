"""Tests for ssh_audit.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import base64
import struct
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ssh_audit as sa  # noqa: E402


def s(b: bytes) -> bytes:
    return struct.pack(">I", len(b)) + b


class SshdTest(unittest.TestCase):
    def test_first_value_wins_and_match_ignored(self) -> None:
        cfg = sa.parse_sshd("PasswordAuthentication no\nPasswordAuthentication yes\n"
                            "Match User bob\n  PasswordAuthentication yes\n")
        self.assertEqual(cfg["passwordauthentication"], "no")

    def test_insecure_sample(self) -> None:
        f = sa.audit_sshd(sa.parse_sshd((HERE / "sample-sshd-effective.txt").read_text(encoding="utf-8")))
        highs = [m for lvl, m in f if lvl == "HIGH"]
        self.assertEqual(len(highs), 2)
        self.assertTrue(any("PermitRootLogin yes" in m for m in highs))

    def test_hardened_sample_clean(self) -> None:
        text = (HERE / "sample-sshd-hardened.conf").read_text(encoding="utf-8")
        self.assertEqual(sa.audit_sshd(sa.parse_sshd(text)), [])

    def test_empty_password_critical(self) -> None:
        self.assertEqual(sa.audit_sshd({"permitemptypasswords": "yes"})[0][0], "CRITICAL")


class KeyTest(unittest.TestCase):
    def test_rsa_bits_from_wire_format(self) -> None:
        n = b"\x00" + b"\xc5" + b"\x11" * 255          # 256 bytes, top bit set → 2048
        blob = base64.b64encode(s(b"ssh-rsa") + s(b"\x01\x00\x01") + s(n)).decode()
        self.assertEqual(sa.rsa_bits(blob), 2048)

    def test_truncated_blob(self) -> None:
        with self.assertRaises(ValueError):
            sa.rsa_bits(base64.b64encode(s(b"ssh-rsa") + b"\x00\x00").decode())

    def test_sample_audit(self) -> None:
        keys = sa.parse_authorized_keys((HERE / "sample-authorized_keys").read_text(encoding="utf-8"))
        self.assertEqual(len(keys), 8)
        self.assertEqual([k.bits for k in keys if k.keytype == "ssh-rsa"], [4096, 2048, 1024])
        self.assertTrue(keys[5].options.startswith('from="10.0.0.0/8"'))
        text = "\n".join(f"{lvl} {m}" for lvl, m in sa.audit_keys(keys))
        self.assertIn("HIGH line 5 (legacy@2012): RSA 1024 bit", text)
        self.assertIn("HIGH line 6 (ancient@server): DSA key", text)
        self.assertIn("MEDIUM line 9 (sami@laptop-copy): duplicate of line 2", text)

    def test_garbage_line(self) -> None:
        with self.assertRaises(ValueError):
            sa.parse_authorized_keys("not a key\n")

    def test_cli(self) -> None:
        self.assertEqual(sa.main(["keys", str(HERE / "sample-authorized_keys")]), 1)
        self.assertEqual(sa.main(["sshd", str(HERE / "sample-sshd-hardened.conf")]), 0)
        self.assertEqual(sa.main(["sshd", str(HERE / "missing")]), 2)


if __name__ == "__main__":
    unittest.main()
