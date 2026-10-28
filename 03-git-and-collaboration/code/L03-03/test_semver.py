"""Tests for semver.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import semver as sv  # noqa: E402

V = sv.Version.parse


class VersionTest(unittest.TestCase):
    def test_spec_precedence_example(self) -> None:
        # semver.org §11-এর উদাহরণ ক্রম
        ordered = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
                   "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]
        self.assertEqual([str(v) for v in sorted(V(x) for x in reversed(ordered))], ordered)

    def test_numeric_not_string_comparison(self) -> None:
        self.assertLess(V("1.9.0"), V("1.10.0"))         # string sort-এ উল্টো হতো
        self.assertLess(V("2.0.0"), V("10.0.0"))

    def test_build_metadata_ignored(self) -> None:
        self.assertEqual(V("1.0.0+build.1"), V("1.0.0+build.2"))
        self.assertEqual(str(V("v1.2.3-rc.1+sha.bea3fb5")), "1.2.3-rc.1+sha.bea3fb5")

    def test_invalid(self) -> None:
        for bad in ("1.0", "01.0.0", "1.0.0-01", "1.0.0-", "1.0.0+", "latest", "1.2.3.4"):
            with self.assertRaises(ValueError, msg=bad):
                V(bad)

    def test_bump(self) -> None:
        self.assertEqual(str(V("1.4.2").bump("patch")), "1.4.3")
        self.assertEqual(str(V("1.4.2").bump("minor")), "1.5.0")
        self.assertEqual(str(V("1.4.2").bump("major")), "2.0.0")
        self.assertEqual(str(V("1.5.0-rc.2").bump("patch")), "1.5.0")


class ConventionalTest(unittest.TestCase):
    def test_classify(self) -> None:
        self.assertEqual(sv.classify("feat(api): add export"), "minor")
        self.assertEqual(sv.classify("fix: null check"), "patch")
        self.assertEqual(sv.classify("feat!: drop v1 endpoints"), "major")
        self.assertEqual(sv.classify("refactor: x\n\nBREAKING CHANGE: config renamed"), "major")
        self.assertIsNone(sv.classify("docs: readme"))
        self.assertIsNone(sv.classify("Updated stuff"))        # convention মানা হয়নি

    def test_next_version(self) -> None:
        self.assertEqual(str(sv.next_version(V("1.4.2"), ["fix: a", "feat: b", "docs: c"])[0]), "1.5.0")
        self.assertEqual(sv.next_version(V("1.4.2"), ["docs: only"]), (None, None))
        self.assertEqual(str(sv.next_version(V("0.3.1"), ["feat!: breaking"])[0]), "0.4.0")   # 0.x নিয়ম


@unittest.skipUnless(shutil.which("git"), "git not installed")
class RepoTest(unittest.TestCase):
    def test_next_from_repo(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="semver-"))
        try:
            cfg = tmp / "empty.cfg"
            cfg.write_text("")
            env = dict(os.environ, GIT_CONFIG_GLOBAL=str(cfg), GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="T",
                       GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.com")

            def git(*a: str) -> None:
                subprocess.run(["git", *a], cwd=tmp / "r", env=env, check=True, capture_output=True)

            subprocess.run(["git", "init", "-q", "-b", "main", "r"], cwd=tmp, env=env, check=True)
            for msg, tag in (("feat: one", "v1.2.0"), ("fix: two", "v1.10.0"), ("feat: three", "v2.0.0-rc.1"),
                             ("fix: four", None)):
                git("commit", "-q", "--allow-empty", "-m", msg)
                if tag:
                    git("tag", tag)
            current, tag = sv.latest_tag(tmp / "r")
            self.assertEqual(tag, "v1.10.0")                   # rc বাদ, 1.10 > 1.2 (numeric)
            msgs = sv.messages_since(tmp / "r", tag)
            self.assertEqual(msgs, ["fix: four", "feat: three"])
            self.assertEqual(str(sv.next_version(current, msgs)[0]), "1.11.0")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
