"""Tests for fs_explorer.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fs_explorer as fe  # noqa: E402


class FhsTest(unittest.TestCase):
    def test_longest_prefix(self) -> None:
        self.assertEqual(fe.fhs_lookup("/var/log/nginx/access.log")[0], "/var/log")
        self.assertEqual(fe.fhs_lookup("/var/spool/cron")[0], "/var")
        self.assertEqual(fe.fhs_lookup("/usr/local/bin/tool")[0], "/usr/local")
        self.assertEqual(fe.fhs_lookup("/weird/place")[0], "/")

    def test_relative_rejected(self) -> None:
        with self.assertRaises(ValueError):
            fe.fhs_lookup("var/log")


class MountsTest(unittest.TestCase):
    def test_sample(self) -> None:
        mounts = fe.parse_mounts((HERE / "sample-mounts.txt").read_text(encoding="utf-8"))
        self.assertEqual(len(mounts), 12)
        by_point = {m.mountpoint: m for m in mounts}
        self.assertEqual(by_point["/"].fstype, "ext4")
        self.assertIn("/mnt/backup disk", by_point)          # \040 → space
        self.assertTrue(by_point["/mnt/backup disk"].read_only)
        self.assertFalse(by_point["/"].read_only)
        real = [m.mountpoint for m in mounts if m.fstype not in fe.PSEUDO_FS]
        self.assertEqual(real, ["/", "/boot", "/boot/efi", "/mnt/backup disk"])


class LinksTest(unittest.TestCase):
    def test_hard_link_survives_delete(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = fe.links_experiment(Path(d))
        joined = "\n".join(out)
        self.assertIn("links=2", joined)            # original + hard link
        self.assertIn("same_inode=True", joined)
        self.assertIn("hard still readable=True links=1", joined)
        if "skipped" not in joined:
            self.assertIn("soft dangling=True", joined)


if __name__ == "__main__":
    unittest.main()
