"""Tests for run_cmd.py — চালানো: python3 -m unittest -v

Child process হিসেবে বর্তমান Python (sys.executable) ব্যবহার — Linux ও Windows দুই জায়গায় চলে।
"""
from __future__ import annotations

import io
import shutil
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_cmd as rc  # noqa: E402

PY = sys.executable


class RunTest(unittest.TestCase):
    def test_success(self) -> None:
        r = rc.run([PY, "-c", "print('hello')"])
        self.assertTrue(r.ok)
        self.assertEqual(r.stdout.strip(), "hello")

    def test_failure_keeps_stderr(self) -> None:
        r = rc.run([PY, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])
        self.assertEqual((r.returncode, r.stderr, r.ok), (3, "boom", False))

    def test_not_found_and_string_rejected(self) -> None:
        self.assertEqual(rc.run(["definitely-not-a-command-xyz"]).returncode, rc.NOT_FOUND_RC)
        with self.assertRaises(TypeError):
            rc.run("echo hi")  # type: ignore[arg-type]

    def test_timeout_kills_tree(self) -> None:
        child = ("import subprocess,sys,time;"
                 "subprocess.Popen([sys.executable,'-c','import time; time.sleep(8)']);"
                 "print('started', flush=True); time.sleep(30)")
        r = rc.run([PY, "-c", child], timeout=1)
        self.assertTrue(r.timed_out)
        self.assertEqual(r.returncode, rc.TIMEOUT_RC)
        self.assertLess(r.duration_s, 6)                 # সাধারণ subprocess.run এখানে ~8 s নিত
        self.assertIn("started", r.stdout)               # timeout-এর আগের output হারায় না

    def test_input_env_and_truncation(self) -> None:
        r = rc.run([PY, "-c", "import os,sys; print(sys.stdin.read().upper(), os.environ['DEMO_X'])"],
                   input_text="abc", extra_env={"DEMO_X": "42"})
        self.assertEqual(r.stdout.strip(), "ABC 42")
        r = rc.run([PY, "-c", "print('x' * 5000)"], max_output=100)
        self.assertTrue(r.truncated)
        self.assertLess(len(r.stdout), 200)

    def test_arguments_are_not_interpreted(self) -> None:
        payload = "a; echo INJECTED $(whoami) `id`"
        r = rc.run([PY, "-c", "import sys; print(sys.argv[1])", payload])
        self.assertEqual(r.stdout.strip(), payload)
        self.assertIn("'a; echo", r.cmdline)              # shlex.join quoting

    @unittest.skipIf(shutil.which("bash") is None, "bash needed")
    def test_shell_string_is_injectable(self) -> None:
        bash = shutil.which("bash")
        assert bash is not None
        unsafe = subprocess.run([bash, "-c", "echo processing report.txt; echo INJECTED"],
                                capture_output=True, text=True, check=True)
        self.assertEqual(unsafe.stdout.splitlines(), ["processing report.txt", "INJECTED"])


class CliTest(unittest.TestCase):
    def test_json_and_exit_code(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = rc.main(["--json", "--", PY, "-c", "raise SystemExit(5)"])
        self.assertEqual(code, 5)
        self.assertIn('"returncode": 5', out.getvalue())


if __name__ == "__main__":
    unittest.main()
