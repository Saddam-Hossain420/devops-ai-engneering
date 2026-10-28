"""Tests for logscan.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import gzip
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logscan as ls  # noqa: E402

OK = '192.0.2.1 - - [27/Oct/2026:09:00:01 +0000] "GET /api/tasks?page=2 HTTP/1.1" 200 512 "-" "curl/8" 0.042'


class ParseTest(unittest.TestCase):
    def test_full_line(self) -> None:
        r = ls.parse(OK)
        assert r is not None
        self.assertEqual((r.ip, r.method, r.path, r.status, r.size, r.rt), ("192.0.2.1", "GET", "/api/tasks", 200, 512, 0.042))

    def test_variants(self) -> None:
        no_rt = '192.0.2.1 - - [27/Oct/2026:09:00:01 +0000] "GET / HTTP/1.1" 304 - "-" "x"'
        common = '192.0.2.1 - - [27/Oct/2026:09:00:01 +0000] "GET / HTTP/1.1" 200 10'
        escaped = r'192.0.2.1 - - [27/Oct/2026:09:00:01 +0000] "GET /a\"b HTTP/1.1" 400 0 "-" "x" 0.001'
        self.assertEqual(ls.parse(no_rt).size, 0)
        self.assertIsNone(ls.parse(no_rt).rt)
        self.assertEqual(ls.parse(common).status, 200)                     # referer/agent ছাড়া (common format)
        self.assertEqual(ls.parse(escaped).path, r"/a\"b")
        for bad in ("garbage", OK.replace("27/Oct/2026", "32/Oct/2026"), OK.replace('" 200', '" 2000')):
            with self.subTest(bad=bad[:40]):
                self.assertIsNone(ls.parse(bad))

    def test_percentile_nearest_rank(self) -> None:
        values = [float(v) for v in range(1, 101)]
        self.assertEqual([ls.percentile(values, p) for p in (50, 90, 99, 100)], [50.0, 90.0, 99.0, 100.0])
        self.assertEqual(ls.percentile([7.0], 99), 7.0)
        self.assertIsNone(ls.percentile([], 50))


class AnalyzeTest(unittest.TestCase):
    def lines(self) -> list[str]:
        out = []
        for minute in range(3):
            for i in range(30):
                status = 503 if minute == 1 and i < 6 else 200
                out.append(f'192.0.2.{i % 3} - - [27/Oct/2026:09:0{minute}:{i:02d} +0000] '
                           f'"GET /p{i % 2} HTTP/1.1" {status} 100 "-" "x" 0.{i:03d}')
        return out + ["broken line", ""]

    def test_counts_and_spikes(self) -> None:
        s = ls.analyze(self.lines())
        self.assertEqual((s.total, s.unparsed, s.status["5xx"]), (90, 1, 6))
        self.assertEqual(ls.spikes(s, 0.05, 20), [("09:01", 30, 6)])
        self.assertEqual(ls.spikes(s, 0.05, 31), [])                          # কম request-এর মিনিট বাদ

    def test_time_window(self) -> None:
        s = ls.analyze(self.lines(), since=time(9, 1), until=time(9, 2))
        self.assertEqual(s.total, 30)

    def test_gzip_detected_by_content(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "access.log.1")                                        # নামে .gz নেই
            p.write_bytes(gzip.compress(("\n".join(self.lines()) + "\n").encode()))
            self.assertEqual(ls.analyze(ls.lines_from([str(p)])).total, 90)


class CliTest(unittest.TestCase):
    def test_generated_log_finds_incident(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            log = Path(d, "access.log")
            with log.open("wb") as f:
                subprocess.run([sys.executable, str(HERE / "gen_access_log.py"), "--lines", "6000"],
                               stdout=f, check=True, timeout=60)
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()):
                code = ls.main([str(log), "--json", "--min-requests", "50"])
        rep = json.loads(out.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(rep["unparsed_lines"], 5)
        self.assertEqual([m["minute"] for m in rep["spike_minutes"]], ["09:20", "09:21", "09:22", "09:23", "09:24"])
        self.assertEqual(rep["top_5xx_paths"][0][0], "/api/orders")
        self.assertEqual(rep["top_clients"][0][0], "203.0.113.66")

    def test_missing_file_and_bad_time(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(ls.main([str(HERE / "nope.log")]), 2)
            with self.assertRaises(SystemExit):
                ls.main([str(HERE / "nope.log"), "--since", "25:99"])


if __name__ == "__main__":
    unittest.main()
