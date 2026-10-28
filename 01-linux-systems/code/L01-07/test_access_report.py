"""Tests for access_report.py — চালানো: python3 -m unittest -v

শেষ test-টি আসল shell pipeline (awk | sort | uniq -c) চালিয়ে Python-এর ফলের সাথে মেলায়।
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import access_report as ar  # noqa: E402


class ParseTest(unittest.TestCase):
    def test_line(self) -> None:
        r = ar.parse_line('203.0.113.10 - - [26/Oct/2026:09:00:00 +0000] "GET /tasks HTTP/1.1" 200 8585 '
                          '"-" "curl/8.5.0" 0.052')
        self.assertEqual((r.ip, r.method, r.path, r.status, r.size, r.request_time),
                         ("203.0.113.10", "GET", "/tasks", 200, 8585, 0.052))

    def test_dash_size_no_time_and_garbage(self) -> None:
        r = ar.parse_line('192.0.2.1 - - [x] "GET / HTTP/1.1" 304 - "-" "ua"')
        self.assertEqual((r.size, r.request_time), (0, None))
        self.assertIsNone(ar.parse_line("not a log line"))


class ReportTest(unittest.TestCase):
    def setUp(self) -> None:
        lines = (HERE / "access.log").read_text(encoding="utf-8").splitlines()
        self.reqs = [r for r in map(ar.parse_line, lines) if r]

    def test_sample(self) -> None:
        rep = ar.report(self.reqs, top=3, slow=1.0)
        self.assertEqual(rep["total"], 300)
        self.assertEqual(rep["status_counts"], [(200, 265), (404, 27), (500, 8)])
        self.assertEqual(rep["error_5xx_percent"], 2.7)
        self.assertEqual(rep["top_ips"][0], ("203.0.113.10", 93))
        self.assertEqual(rep["top_404_paths"], [("/wp-login.php", 22), ("/tasks/999", 5)])
        self.assertEqual(rep["slow_paths"], [("/api/export", 8)])
        self.assertEqual(rep["bytes_sent"], 1194496)

    @unittest.skipUnless(shutil.which("bash") and shutil.which("awk"), "bash/awk not available")
    def test_matches_shell_pipeline(self) -> None:
        # full path: Windows-এ শুধু "bash" দিলে System32-এর WSL bash.exe চলে যেতে পারে
        bash = shutil.which("bash")
        out = subprocess.run([bash, "-c", "awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -3"],
                             cwd=HERE, capture_output=True, text=True, check=True).stdout
        shell = [(line.split()[1], int(line.split()[0])) for line in out.strip().splitlines()]
        self.assertEqual(shell, ar.report(self.reqs, 3, 1.0)["top_ips"])


if __name__ == "__main__":
    unittest.main()
