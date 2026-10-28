"""Tests for strict_mode_demo.sh and script_template.sh — চালানো: python3 -m unittest -v

আসল bash চালিয়ে strict mode-এর আচরণ যাচাই (bash ৪.৪+ দরকার: inherit_errexit)।
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASH = shutil.which("bash")    # পূর্ণ path — Windows-এ শুধু "bash" WSL চালাতে পারে


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([BASH, *args], capture_output=True, text=True, encoding="utf-8", timeout=60)


@unittest.skipUnless(BASH, "bash not installed")
class StrictModeDemoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        out = run(str(HERE / "strict_mode_demo.sh")).stdout
        cls.results = {int(m[1]): m[2] for m in re.finditer(r"^(\d+)\s.*?\s(continued|STOPPED)\s", out, re.M)}

    def test_all_cases_ran(self) -> None:
        self.assertEqual(sorted(self.results), list(range(1, 19)))

    def test_where_set_e_is_silent(self) -> None:
        for case in (3, 4, 5, 6, 7, 9, 15):        # if, &&, ||, function-in-if, local, pipe, subshell
            self.assertEqual(self.results[case], "continued", case)

    def test_where_it_stops(self) -> None:
        for case in (2, 8, 10, 11, 13, 16, 17, 18):
            self.assertEqual(self.results[case], "STOPPED", case)

    def test_arithmetic_pitfall(self) -> None:
        self.assertEqual((self.results[11], self.results[12]), ("STOPPED", "continued"))


@unittest.skipUnless(BASH, "bash not installed")
class TemplateTest(unittest.TestCase):
    script = str(HERE / "script_template.sh")

    def test_syntax_and_help(self) -> None:
        self.assertEqual(run("-n", self.script).returncode, 0)
        r = run(self.script, "-h")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage:", r.stdout)

    def test_usage_errors_exit_2(self) -> None:
        self.assertEqual(run(self.script).returncode, 2)
        self.assertEqual(run(self.script, "-x", "a").returncode, 2)
        self.assertEqual(run(self.script, "a", "b").returncode, 2)

    def test_dry_run_single_line_and_stdout_clean(self) -> None:
        r = run(self.script, "-n", "world")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "hello, world\n")                     # শুধু ফল stdout-এ
        self.assertRegex(r.stderr, r"dry-run: mkdir -p -- /tmp/world-demo\n")   # IFS join bug-এর regression

    def test_input_validation(self) -> None:
        r = run(self.script, "-n", "bad name; rm -rf /")
        self.assertEqual(r.returncode, 1)
        self.assertIn("ERROR", r.stderr)


if __name__ == "__main__":
    unittest.main()
