"""Tests for opsctl.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import argparse
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import opsctl  # noqa: E402

DiskUsage = type(__import__("shutil").disk_usage(HERE))


def run_main(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = opsctl.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ParserTest(unittest.TestCase):
    def test_global_option_before_or_after_subcommand(self) -> None:
        p = opsctl.build_parser()
        self.assertTrue(p.parse_args(["--json", "disk", "/"]).json)      # SUPPRESS-এর কারণে হারায় না
        self.assertTrue(p.parse_args(["disk", "/", "--json"]).json)
        self.assertFalse(hasattr(p.parse_args(["disk", "/"]), "json"))

    def test_validators(self) -> None:
        self.assertEqual(opsctl.host_port("[::1]:22"), ("::1", 22))
        self.assertEqual(opsctl.host_port("db.internal:5432"), ("db.internal", 5432))
        for bad in ("db", ":22", "h:0", "h:70000", "h:x"):
            with self.subTest(bad=bad), self.assertRaises(argparse.ArgumentTypeError):
                opsctl.host_port(bad)
        with self.assertRaises(argparse.ArgumentTypeError):
            opsctl.percent("101")

    def test_usage_errors_are_64(self) -> None:
        self.assertEqual(run_main()[0], opsctl.EX_USAGE)
        self.assertEqual(run_main("disk", "/", "--warn", "150")[0], opsctl.EX_USAGE)
        code, _, err = run_main("disk", "/", "--warn", "95", "--crit", "90")
        self.assertEqual(code, opsctl.EX_USAGE)
        self.assertIn("must be lower than", err)

    def test_help_and_version_are_0(self) -> None:
        self.assertEqual(run_main("--help")[0], 0)
        code, out, _ = run_main("--version")
        self.assertEqual((code, out.strip()), (0, f"opsctl {opsctl.__version__}"))

    def test_env_default_for_timeout(self) -> None:
        with mock.patch.dict(os.environ, {"OPSCTL_TIMEOUT": "7.5"}):
            self.assertEqual(opsctl.build_parser().parse_args(["port", "h:1"]).timeout, 7.5)


class ChecksTest(unittest.TestCase):
    def test_disk_thresholds(self) -> None:
        gib = 2**30
        with mock.patch.object(opsctl.shutil, "disk_usage", return_value=DiskUsage(100 * gib, 85 * gib, 15 * gib)):
            self.assertEqual(opsctl.check_disk("/", 80, 90).status, opsctl.WARNING)
            self.assertEqual(opsctl.check_disk("/", 90, 95).status, opsctl.OK)
            self.assertEqual(opsctl.check_disk("/", 50, 85).status, opsctl.CRITICAL)
        self.assertEqual(opsctl.check_disk(str(HERE / "no-such-dir"), 80, 90).status, opsctl.UNKNOWN)

    def test_worst_ranks_critical_above_unknown(self) -> None:
        self.assertEqual(opsctl.worst([opsctl.UNKNOWN, opsctl.CRITICAL, opsctl.OK]), opsctl.CRITICAL)
        self.assertEqual(opsctl.worst([opsctl.WARNING, opsctl.UNKNOWN]), opsctl.UNKNOWN)

    def test_port_open_and_closed(self) -> None:
        with socket.socket() as srv:
            srv.bind(("127.0.0.1", 0))
            srv.listen()
            port = srv.getsockname()[1]
            self.assertEqual(opsctl.check_port(("127.0.0.1", port), 2).status, opsctl.OK)
        self.assertEqual(opsctl.check_port(("127.0.0.1", port), 3).status, opsctl.CRITICAL)

    def test_json_quiet_and_exit(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            code, out, _ = run_main("--json", "-q", "disk", d, str(Path(d) / "missing"), "--warn", "99", "--crit", "100")
        doc = json.loads(out)
        self.assertEqual([c["status"] for c in doc["checks"]], ["unknown"])      # -q: OK বাদ
        self.assertEqual(code, opsctl.UNKNOWN)


class ProcessTest(unittest.TestCase):
    def test_closed_pipe_is_quiet(self) -> None:
        proc = subprocess.Popen([sys.executable, str(HERE / "opsctl.py"), "disk", str(HERE)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None
        proc.stdout.close()                                  # পাঠক লেখার আগেই চলে গেল
        proc.wait(timeout=30)                                # communicate() বন্ধ stdout পড়তে চাইত
        assert proc.stderr is not None
        err = proc.stderr.read()
        proc.stderr.close()
        self.assertEqual(proc.returncode, 141)
        self.assertNotIn(b"Traceback", err)


if __name__ == "__main__":
    unittest.main()
