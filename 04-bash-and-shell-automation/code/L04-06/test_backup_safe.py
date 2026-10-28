"""Tests for backup_safe.sh — চালানো: python3 -m unittest -v

আসল bash, tar ও find চালায় temporary directory-তে। Concurrency test bash-এর ভেতরে background run দিয়ে।
এই machine-এ flock না থাকলে mkdir fallback-ই test হয়; Ubuntu-তে flock পথ।
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASH = shutil.which("bash")
SCRIPT = (HERE / "backup_safe.sh").as_posix()
HAS_FLOCK = shutil.which("flock") is not None


def sh(code: str, env: dict[str, str] | None = None, timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, "-c", code], capture_output=True, text=True, encoding="utf-8",
                          timeout=timeout, env=dict(os.environ, **(env or {})))


@unittest.skipUnless(BASH and shutil.which("tar") and shutil.which("sha256sum"), "bash/tar/sha256sum missing")
class BackupSafeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="bsafe-"))
        self.src = self.tmp / "app"
        self.src.mkdir()
        (self.src / "a.txt").write_text("v1")
        self.dest = self.tmp / "bk"
        self.S, self.D = self.src.as_posix(), self.dest.as_posix()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def backup(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        return sh(f'bash "{SCRIPT}" -s "{self.S}" -d "{self.D}" ' + " ".join(args), env=env)

    def archives(self) -> list[str]:
        return sorted(p.name for p in self.dest.glob("app-*.tar.gz")) if self.dest.exists() else []

    def test_idempotent_skip_then_change(self) -> None:
        self.assertEqual(self.backup().returncode, 0)
        r = self.backup()
        self.assertEqual(r.returncode, 0)
        self.assertIn("unchanged", r.stderr)
        self.assertEqual(len(self.archives()), 1)
        time.sleep(1.1)                                       # নাম-এ সেকেন্ড-ভিত্তিক timestamp
        (self.src / "a.txt").write_text("v2-changed")
        self.assertEqual(self.backup().returncode, 0)
        self.assertEqual(len(self.archives()), 2)

    def test_concurrent_run_gets_75(self) -> None:
        r = sh(f'bash "{SCRIPT}" -f -H 3 -s "{self.S}" -d "{self.D}" 2>/dev/null & p=$!; sleep 1.2; '
               f'bash "{SCRIPT}" -f -s "{self.S}" -d "{self.D}"; echo "second=$?"; wait $p; echo "first=$?"')
        self.assertIn("second=75", r.stdout)
        self.assertIn("first=0", r.stdout)
        self.assertIn("another backup", r.stderr)

    @unittest.skipIf(HAS_FLOCK, "flock path does not use the mkdir lock directory")
    def test_stale_lock_is_taken_over(self) -> None:
        lock = self.dest / ".lock.d"
        lock.mkdir(parents=True)
        (lock / "pid").write_text("999999")
        r = self.backup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("stale lock", r.stderr)
        self.assertFalse(lock.exists())                       # শেষে lock মুক্ত

    def test_dry_run_rotation_matches_real(self) -> None:
        for _ in range(3):
            self.assertEqual(self.backup("-f", "-q", "-k", "0").returncode, 0)
            time.sleep(1.1)
        before = self.archives()
        dry = self.backup("-f", "-k", "2", "-n")
        self.assertEqual(self.archives(), before)             # dry-run কিছু মোছেনি
        planned = dry.stderr.count("dry-run: rm -f")
        self.backup("-f", "-q", "-k", "2")
        removed = len(set(before) - set(self.archives()))
        self.assertEqual((planned, removed, len(self.archives())), (2, 2, 2))

    def test_failed_tar_leaves_no_partial_and_no_lock(self) -> None:
        fake = self.tmp / "fakebin"
        fake.mkdir()
        (fake / "tar").write_text('#!/usr/bin/env bash\necho "fake tar failure" >&2\nexit 1\n', newline="\n")
        (fake / "tar").chmod(0o755)
        # PATH-এর অংশ ':' দিয়ে আলাদা — "C:/..." দুই ভাগ হয়ে যেত; তাই shell-এর নিজের রূপে (`cd && pwd`)
        r = sh(f'PATH="$(cd "{fake.as_posix()}" && pwd):$PATH" bash "{SCRIPT}" -s "{self.S}" -d "{self.D}"')
        self.assertIn("fake tar failure", r.stderr)          # নকল tar সত্যিই চলেছে
        self.assertEqual(r.returncode, 1)
        leftovers = [p.name for p in self.dest.iterdir()]
        self.assertEqual([n for n in leftovers if n.startswith(".partial") or n.startswith(".lock")], [])
        self.assertNotIn(".last-fingerprint", leftovers)      # ব্যর্থ run "অপরিবর্তিত" রেকর্ড করেনি

    def test_usage(self) -> None:
        self.assertEqual(sh(f'bash "{SCRIPT}"').returncode, 2)
        self.assertEqual(self.backup("-k", "x").returncode, 2)
        self.assertEqual(sh(f'bash "{SCRIPT}" -s "{self.S}" -d "{self.S}/inner"').returncode, 2)


if __name__ == "__main__":
    unittest.main()
