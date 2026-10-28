"""Tests for ps_tree.py and graceful_worker.py — চালানো: python3 -m unittest -v

Signal test শুধু POSIX (Linux)-এ চলে; Windows-এ skip।
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ps_tree as pt  # noqa: E402


class PsTreeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.procs = pt.parse_ps((HERE / "sample-ps.txt").read_text(encoding="utf-8"))

    def test_parse(self) -> None:
        self.assertEqual(len(self.procs), 18)
        self.assertEqual(self.procs[14].comm, "kworker/0:1H-kblockd")
        self.assertEqual(self.procs[1250].state, "Z")

    def test_tree_structure(self) -> None:
        tree = pt.render_tree(self.procs, 1200)
        self.assertEqual(tree[0], "taskflow-api (1200) [Ss] app")
        self.assertEqual(len(tree), 5)
        self.assertTrue(tree[-1].startswith("└─ python3 (1252)"))

    def test_warnings(self) -> None:
        w = pt.warnings(self.procs)
        self.assertIn("ZOMBIE: 3 zombie child(ren) of taskflow-api (1200)", w[0])
        self.assertTrue(any("D-STATE: rsync (2100)" in x for x in w))

    def test_cli(self) -> None:
        self.assertEqual(pt.main([str(HERE / "sample-ps.txt")]), 1)            # warnings
        self.assertEqual(pt.main([str(HERE / "sample-ps.txt"), "--root", "655"]), 1)
        self.assertEqual(pt.main([str(HERE / "sample-ps.txt"), "--root", "9999"]), 2)


@unittest.skipUnless(os.name == "posix", "POSIX signals required")
class SignalTest(unittest.TestCase):
    def start(self) -> subprocess.Popen:
        proc = subprocess.Popen([sys.executable, str(HERE / "graceful_worker.py"), "--job-seconds", "0.3"],
                                stdout=subprocess.PIPE, text=True)
        assert proc.stdout is not None
        proc.stdout.readline()  # "started" — handler বসানো নিশ্চিত
        return proc

    def test_sigterm_is_graceful(self) -> None:
        proc = self.start()
        time.sleep(0.5)
        proc.send_signal(signal.SIGHUP)
        time.sleep(0.1)
        proc.send_signal(signal.SIGTERM)
        out, _ = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("SIGHUP: reloading config", out)
        self.assertIn("clean shutdown", out)

    def test_sigkill_cannot_be_caught(self) -> None:
        proc = self.start()
        proc.send_signal(signal.SIGKILL)
        out, _ = proc.communicate(timeout=5)
        self.assertEqual(proc.returncode, -signal.SIGKILL)  # Python: negative = killed by signal
        self.assertNotIn("clean shutdown", out)


if __name__ == "__main__":
    unittest.main()
