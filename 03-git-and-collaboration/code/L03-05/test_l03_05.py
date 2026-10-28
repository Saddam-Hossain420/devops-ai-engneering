"""Tests for lost_commits.py and the demo scripts — চালানো: python3 -m unittest -v

Temporary repository-তে আসল git দিয়ে "দুর্ঘটনা" ঘটিয়ে tool-এর ফল যাচাই। Global config ব্যবহার হয় না।
"""
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

import lost_commits as lc  # noqa: E402

GIT = shutil.which("git")
BASH = shutil.which("bash")


@unittest.skipUnless(GIT, "git not installed")
class LostCommitsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="lost-"))
        cfg = self.tmp / "c"
        cfg.write_text("")
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=str(cfg), GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.com")
        os.environ.update({k: self.env[k] for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM")})
        self.repo = self.tmp / "r"
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.tmp)
        for n in range(1, 5):
            (self.repo / "f.txt").write_text(str(n))
            self.git("add", ".")
            self.git("commit", "-q", "-m", f"c{n}")

    def tearDown(self) -> None:
        for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run([GIT, *args], cwd=cwd or self.repo, env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_nothing_lost(self) -> None:
        self.assertEqual(lc.lost_from_reflog(self.repo), [])

    def test_reset_hard_reports_one_tip(self) -> None:
        tip = self.git("rev-parse", "HEAD")
        self.git("reset", "-q", "--hard", "HEAD~2")
        lost = lc.lost_from_reflog(self.repo)
        self.assertEqual([s for s, _, _ in lost], [tip])        # c3 c4-এর পূর্বপুরুষ — আলাদা দেখায় না

    def test_deleted_branch_and_rescue(self) -> None:
        self.git("switch", "-q", "-c", "exp")
        (self.repo / "x.txt").write_text("x")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "exp work")
        sha = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "main")
        self.git("branch", "-D", "exp")
        self.assertEqual([s for s, _, _ in lc.lost_from_reflog(self.repo)], [sha])
        self.git("branch", "rescue", sha)
        self.assertEqual(lc.lost_from_reflog(self.repo), [])

    def test_fsck_finds_commit_after_reflog_expired(self) -> None:
        tip = self.git("rev-parse", "HEAD")
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.git("reflog", "expire", "--expire=now", "--all")
        self.assertEqual(lc.lost_from_reflog(self.repo), [])    # reflog-এ আর নেই
        self.assertIn(tip, lc.unreachable_from_fsck(self.repo))  # কিন্তু object এখনো আছে (gc-র আগে)

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(lc.main(["--repo", str(self.repo)]), 0)
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.assertEqual(lc.main(["--repo", str(self.repo)]), 1)
        self.assertEqual(lc.main(["--repo", str(self.tmp / "missing")]), 2)


@unittest.skipUnless(GIT and BASH, "git/bash not installed")
class DemoScriptTest(unittest.TestCase):
    def run_demo(self, name: str) -> str:
        tmp = Path(tempfile.mkdtemp(prefix="demo-"))
        try:
            r = subprocess.run([BASH, str(HERE / name), str(tmp / "d")], capture_output=True, text=True,
                               encoding="utf-8", timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_bisect_finds_change_21(self) -> None:
        out = self.run_demo("bisect_demo.sh")
        self.assertIn("→ change 21", out)
        self.assertIn("steps: 5 test runs", out)

    def test_recovery_demo(self) -> None:
        out = self.run_demo("recovery_demo.sh")
        self.assertIn("-- restored: 2759ef6 experiment: promising idea", out)
        self.assertIn("config.txt exists after revert? no", out)


if __name__ == "__main__":
    unittest.main()
