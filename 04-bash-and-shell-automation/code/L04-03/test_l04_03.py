"""Tests for lib/common.sh and disk_check.sh — চালানো: python3 -m unittest -v

Library function আসল bash-এ source করে পরীক্ষা; disk_check হাতে তৈরি df output দিয়ে।
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASH = shutil.which("bash")
LIB = (HERE / "lib" / "common.sh").as_posix()


def sh(code: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """lib source করে code চালানো।"""
    env = dict(os.environ, **(env_extra or {}))
    return subprocess.run([BASH, "-c", f'set -Eeuo pipefail; source "{LIB}"; {code}'], capture_output=True,
                          text=True, encoding="utf-8", timeout=60, env=env)


def check(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, str(HERE / "disk_check.sh"), *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=60, cwd=HERE)


@unittest.skipUnless(BASH, "bash not installed")
class LibraryTest(unittest.TestCase):
    def test_refuses_direct_execution_and_double_source_is_safe(self) -> None:
        r = subprocess.run([BASH, LIB], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(sh(f'source "{LIB}"; echo ok').stdout, "ok\n")      # readonly-তে error নেই

    def test_join_and_to_bytes(self) -> None:
        r = sh('join_by ", " a "b c" d; join_by - solo; to_bytes 1.5M; to_bytes 2g; to_bytes 512; '
               'to_bytes 10XB || echo invalid')
        self.assertEqual(r.stdout.split("\n")[:6], ["a, b c, d", "solo", "1572864", "2147483648", "512", "invalid"])

    def test_is_true_and_require_cmd(self) -> None:
        self.assertEqual(sh("is_true On && is_true 1 && ! is_true no && echo ok").stdout, "ok\n")
        r = sh("require_cmd bash missing_cmd_a missing_cmd_b || echo rc=$?")
        self.assertIn("rc=1", r.stdout)
        self.assertIn("missing_cmd_a missing_cmd_b", r.stderr)               # সবগুলো একবারে

    def test_log_levels(self) -> None:
        r = sh("log_debug hidden; log_info shown; log_error bad", {"LOG_LEVEL": "info"})
        self.assertNotIn("hidden", r.stderr)
        self.assertIn("INFO", r.stderr)
        self.assertEqual(r.stdout, "")                                       # log কখনো stdout-এ নয়

    def test_retry_succeeds_after_failures(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            counter = Path(d, "n").as_posix()
            flaky = f'flaky() {{ n=$(( $(cat "{counter}" 2>/dev/null || echo 0) + 1 )); echo $n > "{counter}"; (( n >= 3 )); }}'
            r = sh(f"{flaky}; retry 5 0 flaky && echo done")
            self.assertEqual(r.stdout, "done\n")
            self.assertEqual(r.stderr.count("retrying"), 2)

    def test_retry_gives_up_with_last_status(self) -> None:
        r = sh("retry 2 0 bash -c 'exit 7' || echo rc=$?")
        self.assertIn("rc=7", r.stdout)
        self.assertIn("giving up after 2", r.stderr)


@unittest.skipUnless(BASH, "bash not installed")
class DiskCheckTest(unittest.TestCase):
    def test_sample_states_and_exit(self) -> None:
        r = check("-i", "sample-df.txt")
        self.assertEqual(r.returncode, 2)                                    # CRITICAL আছে
        self.assertIn("WARNING  /var/lib/postgresql (xfs) 84%", r.stdout)
        self.assertIn("CRITICAL /var/log (ext4) 94%", r.stdout)
        self.assertIn("OK       /mnt/backup disk (ext4) 12%", r.stdout)       # mount-এ space
        self.assertNotIn("tmpfs", r.stdout)                                  # default exclude

    def test_thresholds(self) -> None:
        self.assertEqual(check("-i", "sample-df.txt", "-w", "85", "-c", "95").returncode, 1)
        self.assertEqual(check("-i", "sample-df.txt", "-w", "95", "-c", "99").returncode, 0)
        self.assertEqual(check("-i", "sample-df.txt", "-w", "90", "-c", "80").returncode, 3)
        self.assertEqual(check("-w").returncode, 3)

    def test_source_with_spaces_parses(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d, "df.txt")
            f.write_text("Filesystem Type 1024-blocks Used Available Capacity Mounted on\n"
                         "C:/Program Files/Git ntfs 324094972 267916184 56178788 83% /\n", encoding="utf-8")
            r = check("-i", str(f))
            self.assertEqual(r.stdout, "WARNING  / (ntfs) 83%\n")             # এই machine-এর আসল df-এর লাইন


if __name__ == "__main__":
    unittest.main()
