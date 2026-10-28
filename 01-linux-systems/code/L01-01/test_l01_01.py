"""Tests for syscall_demo.py and strace_summary.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import errno
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import strace_summary as ss  # noqa: E402
import syscall_demo as sd  # noqa: E402


class DemoTest(unittest.TestCase):
    def test_demo_steps_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            steps = sd.demo(d)
            self.assertEqual(steps[2], "write -> 13 bytes")
            self.assertEqual(steps[5], "stat -> size 13")
            self.assertIn(f"errno {errno.ENOENT}", steps[6])
            self.assertEqual(list(Path(d).iterdir()), [])  # unlink worked


class ParseTest(unittest.TestCase):
    def test_success_and_error_lines(self) -> None:
        ok = ss.parse_line('openat(AT_FDCWD, "/etc/hostname", O_RDONLY) = 3')
        self.assertEqual((ok.name, ok.ret, ok.errno), ("openat", "3", None))
        bad = ss.parse_line('access("/etc/ld.so.preload", R_OK)      = -1 ENOENT (No such file or directory)')
        self.assertEqual((bad.name, bad.ret, bad.errno), ("access", "-1", "ENOENT"))

    def test_pid_prefix_and_noise(self) -> None:
        self.assertEqual(ss.parse_line("4242 close(3) = 0").name, "close")
        self.assertIsNone(ss.parse_line("+++ exited with 0 +++"))
        self.assertIsNone(ss.parse_line("--- SIGCHLD {si_signo=SIGCHLD} ---"))

    def test_sample_trace(self) -> None:
        lines = (HERE / "sample-trace.txt").read_text(encoding="utf-8").splitlines()
        calls = [c for c in map(ss.parse_line, lines) if c]
        counts, errors, opened = ss.summarize(calls)
        self.assertEqual(len(calls), 24)
        self.assertEqual(counts["close"], 5)
        self.assertEqual(errors[("access", "ENOENT")], 1)
        self.assertEqual(errors[("openat", "ENOENT")], 1)
        self.assertEqual([ss.first_string_arg(c.args) for c in opened],
                         ["/etc/ld.so.cache", "/lib/x86_64-linux-gnu/libc.so.6", "/etc/hostname"])

    def test_cli(self) -> None:
        self.assertEqual(ss.main([str(HERE / "sample-trace.txt")]), 0)
        self.assertEqual(ss.main([str(HERE / "nope.txt")]), 2)


if __name__ == "__main__":
    unittest.main()
