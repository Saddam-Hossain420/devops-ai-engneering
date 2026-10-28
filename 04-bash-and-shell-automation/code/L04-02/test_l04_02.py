"""Tests for expansion_lab.sh and rename_ext.sh — চালানো: python3 -m unittest -v

আসল bash চালায়; rename test temporary directory-তে কঠিন নামের file দিয়ে।
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASH = shutil.which("bash")


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, *args], capture_output=True, text=True, encoding="utf-8", timeout=60)


@unittest.skipUnless(BASH, "bash not installed")
class ExpansionLabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        r = run(str(HERE / "expansion_lab.sh"))
        assert r.returncode == 0, r.stderr
        cls.vals = {m[1].strip(): m[2] for m in re.finditer(r"^(.*?)→ \[(.*)\]$", r.stdout, re.M)}

    def get(self, key_start: str) -> str:
        return next(v for k, v in self.vals.items() if k.startswith(key_start))

    def test_string_trimming(self) -> None:
        self.assertEqual(self.get("${path##*/}"), "access.log.2.gz")
        self.assertEqual(self.get("${path%/*}"), "/var/log/nginx")
        self.assertEqual(self.get("${path%.*}"), "/var/log/nginx/access.log.2")
        self.assertEqual(self.get("${path%%.*}"), "/var/log/nginx/access")
        self.assertEqual(self.get("${path//log/LOG}"), "/var/LOG/nginx/access.LOG.2.gz")

    def test_unset_vs_empty(self) -> None:
        self.assertEqual(self.get("${EMPTY:-default}"), "default")
        self.assertEqual(self.get("${EMPTY-default}"), "")            # ':' ছাড়া: শুধু unset-এ default
        self.assertEqual(self.get("${UNSET:?is required}"), "error, exit 1")

    def test_quoting_arrays(self) -> None:
        self.assertEqual(self.get('for f in "${files[@]}"'), "3")
        self.assertEqual(self.get("for f in ${files[@]}"), "6")        # unquoted: space-এ ভেঙে যায়
        self.assertEqual(self.get("after += and unset [1]"), "0 2 3")  # sparse array

    def test_associative_and_split(self) -> None:
        self.assertEqual(self.get("${port[https]}"), "443")
        self.assertEqual(self.get("IFS=, read"), "10.0.1.5")
        self.assertEqual(self.get("mapfile"), "two words")


@unittest.skipUnless(BASH, "bash not installed")
class RenameTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="rename-"))
        self.names = ["my photo.jpeg", "-dash.jpeg", "plain.jpeg", "keep.png", "clash.jpeg", "clash.jpg",
                      "new\nline.jpeg"]                               # নামে newline — Linux-এ বৈধ
        for n in list(self.names):
            try:
                (self.dir / n).write_text(n)
            except OSError:
                self.names.remove(n)                                  # Windows filesystem-এ newline নিষেধ হলে বাদ

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def listing(self) -> set[str]:
        return {p.name for p in self.dir.iterdir()}

    def test_dry_run_changes_nothing(self) -> None:
        before = self.listing()
        r = run(str(HERE / "rename_ext.sh"), "-n", str(self.dir), "jpeg", "jpg")
        self.assertEqual(r.returncode, 1)                             # clash skip → 1
        self.assertIn("would rename: my\\ photo.jpeg -> my\\ photo.jpg", r.stdout)
        self.assertEqual(self.listing(), before)

    def test_rename_and_no_overwrite(self) -> None:
        r = run(str(HERE / "rename_ext.sh"), str(self.dir), ".jpeg", ".jpg")
        self.assertEqual(r.returncode, 1)
        after = self.listing()
        self.assertTrue({"my photo.jpg", "-dash.jpg", "plain.jpg", "keep.png"} <= after)
        self.assertIn("clash.jpeg", after)                            # target ছিল → skip
        self.assertEqual((self.dir / "clash.jpg").read_text(), "clash.jpg")   # overwrite হয়নি
        self.assertIn("skip (target exists): clash.jpeg", r.stderr)

    def test_usage_errors(self) -> None:
        script = str(HERE / "rename_ext.sh")
        self.assertEqual(run(script).returncode, 2)
        self.assertEqual(run(script, str(self.dir), "jp-g", "x").returncode, 2)
        self.assertEqual(run(script, str(self.dir / "missing"), "a", "b").returncode, 2)


if __name__ == "__main__":
    unittest.main()
