"""Tests for fs_tools.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import io
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fs_tools as ft  # noqa: E402

NOW = 1_800_000_000.0


class TreeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for rel, size, days in [("a/x.log", 10, 0), ("a/x.1.gz", 500, 20), ("b/big.bin", 9000, 2),
                                ("b/c/old.gz", 5, 90), ("b/c/new.gz", 5, 1)]:
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x" * size)
            os.utime(p, (NOW - days * 86400, NOW - days * 86400))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_largest(self) -> None:
        got = ft.largest(self.root, 2, ft.Walker())
        self.assertEqual([e.path.name for e in got], ["big.bin", "x.1.gz"])

    def test_older_than_pattern_and_order(self) -> None:
        got = ft.older_than(self.root, 14, "*.gz", ft.Walker(), now=NOW)
        self.assertEqual([e.path.name for e in got], ["old.gz", "x.1.gz"])     # পুরোনোটা আগে

    def test_du_depth(self) -> None:
        totals = ft.du(self.root, 1, ft.Walker())
        self.assertEqual(totals[self.root / "b"], 9010)
        self.assertEqual(list(totals)[0], self.root / "b")
        self.assertIn(self.root / "b" / "c", ft.du(self.root, 2, ft.Walker()))

    def test_dry_run_does_not_delete(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = ft.main(["older-than", str(self.root), "--days", "0", "--pattern", "*.gz"])
        self.assertEqual(code, 0)
        self.assertIn("dry-run", out.getvalue())
        self.assertTrue((self.root / "b/c/old.gz").exists())
        with redirect_stdout(io.StringIO()):
            ft.main(["older-than", str(self.root), "--days", "0", "--pattern", "*.gz", "--delete"])
        self.assertFalse((self.root / "b/c/old.gz").exists())
        self.assertTrue((self.root / "b/c").is_dir())                          # directory মোছে না

    def test_symlink_not_followed(self) -> None:
        try:
            os.symlink(self.root / "b", self.root / "a" / "loop", target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"cannot create symlink here: {exc}")
        names = [e.path.name for e in ft.Walker().files(self.root)]
        self.assertEqual(names.count("big.bin"), 1)

    @unittest.skipIf(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                     "POSIX permissions needed, non-root")
    def test_unreadable_dir_is_reported_not_fatal(self) -> None:
        locked = self.root / "b" / "c"
        locked.chmod(0)
        try:
            w = ft.Walker()
            names = [e.path.name for e in w.files(self.root)]
            self.assertIn("big.bin", names)
            self.assertTrue(any("Permission denied" in e for e in w.errors))
        finally:
            locked.chmod(0o755)


class AtomicWriteTest(unittest.TestCase):
    def test_replace_and_no_leftovers(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "app.conf")
            p.write_text("old\n", encoding="utf-8")
            if os.name != "nt":
                p.chmod(0o640)
            ft.atomic_write(p, "new\n")
            self.assertEqual(p.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(os.listdir(d), ["app.conf"])
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o640)      # permission রাখা

    def test_failure_keeps_old_content_and_cleans_temp(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "app.conf")
            p.write_text("old\n", encoding="utf-8")
            with mock.patch.object(ft.os, "replace", side_effect=OSError("disk full")), \
                    self.assertRaises(OSError):
                ft.atomic_write(p, "half-written")
            self.assertEqual(p.read_text(encoding="utf-8"), "old\n")
            self.assertEqual(os.listdir(d), ["app.conf"])


class MiscTest(unittest.TestCase):
    def test_human(self) -> None:
        self.assertEqual([ft.human(x) for x in (5, 2048, 3 * 1024**3)], ["5B", "2.0K", "3.0G"])

    def test_bad_root(self) -> None:
        with redirect_stderr(io.StringIO()):
            self.assertEqual(ft.main(["du", "/definitely/not/here"]), 2)



if __name__ == "__main__":
    unittest.main()
