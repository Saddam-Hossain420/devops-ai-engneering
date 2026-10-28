"""Tests for envcheck.py and pin_check.py — চালানো: python3 -m unittest -v

একটি আসল venv তৈরি করে (stdlib `venv`, `--without-pip` — network বা ensurepip ছাড়া) envcheck সেখানে চালানো হয়।
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import envcheck as ec  # noqa: E402
import pin_check as pc  # noqa: E402


class EnvcheckTest(unittest.TestCase):
    def test_version_parsing(self) -> None:
        self.assertEqual(ec.parse_min_version(">=3.10"), (3, 10))
        self.assertEqual(ec.parse_min_version(">=3.10, <4"), (3, 10))
        with self.assertRaises(ValueError):
            ec.parse_min_version("~=3.10")

    def test_requires_and_pyproject(self) -> None:
        self.assertEqual(ec.requires_from_pyproject(HERE / "sample-pyproject.toml"), ">=3.10")
        self.assertEqual(ec.main(["--requires", ">=3.0"]), 0)
        self.assertEqual(ec.main(["--requires", ">=99.0"]), 1)
        self.assertEqual(ec.main(["--requires", "garbage"]), 2)

    def test_in_venv_logic(self) -> None:
        with mock.patch.object(sys, "prefix", "/venv"), mock.patch.object(sys, "base_prefix", "/usr"):
            self.assertTrue(ec.in_venv())
        with mock.patch.object(sys, "prefix", "/usr"), mock.patch.object(sys, "base_prefix", "/usr"):
            self.assertFalse(ec.in_venv())

    def test_real_venv(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            venv.EnvBuilder(with_pip=False).create(d)
            exe = Path(d) / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            r = subprocess.run([str(exe), str(HERE / "envcheck.py"), "--json", "--require-venv"],
                               capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            info = json.loads(r.stdout)
            self.assertTrue(info["in_venv"])
            self.assertIsNone(info["pip"])                               # --without-pip venv
            self.assertNotEqual(info["prefix"], info["base_prefix"])


class PinCheckTest(unittest.TestCase):
    def test_requirements_classification(self) -> None:
        deps = pc.parse_requirements((HERE / "sample-requirements.txt").read_text(encoding="utf-8"))
        kinds = {d.name: d.kind for d in deps}
        self.assertEqual(kinds["requests"], "pinned")
        self.assertEqual(kinds["urllib3"], "hashed")                     # continuation লাইনের --hash
        self.assertEqual((kinds["pyyaml"], kinds["rich"], kinds["click"]), ("range", "range", "unpinned"))
        self.assertEqual(kinds["psycopg"], "pinned")                     # extra ও marker সহ
        self.assertIn("url", kinds.values())
        self.assertIn("editable", kinds.values())

    def test_modes_and_exit(self) -> None:
        self.assertEqual(pc.main([str(HERE / "sample-requirements.txt")]), 1)
        self.assertEqual(pc.main([str(HERE / "sample-pyproject.toml"), "--mode", "library"]), 1)   # click সীমাহীন
        with tempfile.TemporaryDirectory() as d:
            f = Path(d, "requirements.txt")
            f.write_text("requests==2.32.3\nidna==3.10  # comment\n", encoding="utf-8")
            self.assertEqual(pc.main([str(f)]), 0)
            f.write_text("==broken\n", encoding="utf-8")
            self.assertEqual(pc.main([str(f)]), 2)

    def test_wildcard_is_not_a_pin(self) -> None:
        self.assertEqual(pc.classify("==2.*", False), "range")


if __name__ == "__main__":
    unittest.main()
