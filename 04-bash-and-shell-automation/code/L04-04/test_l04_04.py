"""Tests for trap_demo.sh and safe_job.sh — চালানো: python3 -m unittest -v

আসল bash চালায়। Signal test-এ bash নিজেই `kill -TERM` পাঠায় (Python-এর os.kill Windows-এ bash trap চালায় না)।
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASH = shutil.which("bash")
JOB = (HERE / "safe_job.sh").as_posix()


def run(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout)


@unittest.skipUnless(BASH, "bash not installed")
class TrapDemoTest(unittest.TestCase):
    def test_err_trap_with_E_shows_stack(self) -> None:
        r = run((HERE / "trap_demo.sh").as_posix(), "with-E")
        self.assertEqual(r.returncode, 2)                        # grep-এর exit code বহাল
        self.assertIn("ERR trap: exit 2 at trap_demo.sh:16 running: grep -q '^port=' \"$file\"", r.stderr)
        self.assertIn("at load_config()", r.stderr)
        self.assertIn("at deploy()", r.stderr)
        self.assertNotIn("never reached", r.stdout)

    def test_err_trap_silent_without_E(self) -> None:
        r = run((HERE / "trap_demo.sh").as_posix(), "without-E")
        self.assertEqual(r.returncode, 2)                        # script তবু থামে (set -e)…
        self.assertNotIn("ERR trap", r.stderr)                   # …কিন্তু কেন, কোথায় — কিছু বলে না


@unittest.skipUnless(BASH, "bash not installed")
class SafeJobTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="safejob-"))
        self.out = (self.dir / "out.txt").as_posix()

    def tearDown(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)

    def workdir_gone(self) -> bool:
        wd = Path(self.dir / "out.txt.workdir").read_text().strip()
        r = run("-c", f'[[ -d "{wd}" ]]')
        return r.returncode != 0

    def test_success_cleans_up(self) -> None:
        r = run(JOB, self.out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.dir / "out.txt").read_text().strip(), "500500")
        self.assertTrue(self.workdir_gone())

    def test_failure_cleans_up_and_keeps_exit_code(self) -> None:
        r = run(JOB, "-f", "3", self.out)
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR: 'false' failed", r.stderr)
        self.assertFalse((self.dir / "out.txt").exists())        # publish-এর আগে ব্যর্থ → আধা ফল নেই
        self.assertTrue(self.workdir_gone())

    def test_usage(self) -> None:
        self.assertEqual(run(JOB).returncode, 2)

    def test_sigterm_cleans_up_and_stops_child(self) -> None:
        # sleep-এর অনন্য সময় দিয়ে /proc-এ child খোঁজা; cleanup না থাকলে এটি PPID 1 নিয়ে চলতেই থাকত
        script = f'''
find_sleep() {{ local p; for p in /proc/[0-9]*; do
  [[ "$(tr '\\0' ' ' < "$p/cmdline" 2>/dev/null)" == "sleep 47 " ]] && echo "${{p#/proc/}}"; done; }}
bash "{JOB}" -s 47 "{self.out}" 2>/dev/null & pid=$!
for _ in $(seq 50); do [[ -n $(find_sleep) ]] && break; sleep 0.1; done
echo "during=$(find_sleep | wc -l)"
kill -TERM "$pid"; wait "$pid"; echo "rc=$?"
sleep 0.5; echo "after=$(find_sleep | wc -l)"
'''
        r = run("-c", script)
        if "during=0" in r.stdout:
            self.skipTest("cannot inspect child processes via /proc here")
        self.assertIn("rc=143", r.stdout)
        self.assertIn("after=0", r.stdout)
        self.assertFalse((self.dir / "out.txt").exists())
        self.assertTrue(self.workdir_gone())


if __name__ == "__main__":
    unittest.main()
