"""Tests for argv_show.py and exit_code.py — চালানো: python3 -m unittest -v

Bash-নির্ভর test শুধু তখনই চলে যখন `bash` পাওয়া যায়।
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import argv_show as av  # noqa: E402
import exit_code as ec  # noqa: E402


class ExitCodeTest(unittest.TestCase):
    def test_common_codes(self) -> None:
        self.assertTrue(ec.explain(0).startswith("0: success"))
        self.assertIn("not found", ec.explain(127))
        self.assertIn("not executable", ec.explain(126))
        self.assertIn("SIGKILL", ec.explain(137))
        self.assertIn("SIGTERM", ec.explain(143))
        self.assertIn("SIGINT", ec.explain(130))
        self.assertIn("invalid", ec.explain(300))

    def test_cli(self) -> None:
        self.assertEqual(ec.main(["0", "137"]), 0)
        self.assertEqual(ec.main(["abc"]), 2)
        self.assertEqual(ec.main([]), 2)


class ShlexTest(unittest.TestCase):
    """Python-এর shlex POSIX shell-এর quoting নিয়ম অনুসরণ করে (expansion ছাড়া)।"""

    def test_quoting_rules(self) -> None:
        self.assertEqual(shlex.split("echo hello world"), ["echo", "hello", "world"])
        self.assertEqual(shlex.split('echo "hello world"'), ["echo", "hello world"])
        self.assertEqual(shlex.split("echo 'a \"b\" c'"), ["echo", 'a "b" c'])
        self.assertEqual(shlex.split(r"echo a\ b"), ["echo", "a b"])
        self.assertEqual(shlex.split('echo ""'), ["echo", ""])

    def test_quote_for_safe_command_building(self) -> None:
        dangerous = "x; rm -rf /tmp/demo"
        self.assertEqual(shlex.split("echo " + shlex.quote(dangerous)), ["echo", dangerous])

    def test_describe(self) -> None:
        self.assertEqual(av.describe(["a b", ""]),
                         ["received 2 argument(s)", "  [1] 'a b'", "  [2] ''"])


BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "bash not available")
class BashBehaviourTest(unittest.TestCase):
    def run_bash(self, script: str) -> str:
        return subprocess.run([BASH, "-c", script], capture_output=True, text=True, check=True,
                              cwd=HERE).stdout

    def test_word_splitting_of_unquoted_variable(self) -> None:
        cmd = f'name="my file.txt"; "{sys.executable}" argv_show.py $name "$name"'
        out = self.run_bash(cmd)
        self.assertIn("received 3 argument(s)", out)
        self.assertIn("[3] 'my file.txt'", out)

    def test_exit_status_and_or(self) -> None:
        self.assertEqual(self.run_bash("false; echo $?").strip(), "1")
        self.assertEqual(self.run_bash("false || echo recovered").strip(), "recovered")
        self.assertEqual(self.run_bash("true && echo ran").strip(), "ran")

    def test_parameter_default(self) -> None:
        self.assertEqual(self.run_bash('unset X; echo "${X:-fallback}"').strip(), "fallback")


if __name__ == "__main__":
    unittest.main()
