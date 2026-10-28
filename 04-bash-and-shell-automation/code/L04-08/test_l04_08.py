"""Tests for top_errors.sh / top_errors.py — একই কাজের দুই সংস্করণ। চালানো: python3 -m unittest -v"""
from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gen_log  # noqa: E402
import top_errors as te  # noqa: E402

BASH = shutil.which("bash")


class CompareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="toperr-"))
        for name, args in (("access.log", ["20000"]), ("tricky.log", ["0", "--tricky"])):
            buf = io.StringIO()
            with redirect_stdout(buf):
                gen_log.main(args)
            (cls.tmp / name).write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def py(self, name: str, n: int = 10) -> dict:
        with open(self.tmp / name, encoding="utf-8") as f:
            return te.top_errors(f, n)

    def sh(self, name: str, n: int = 10) -> dict:
        r = subprocess.run([BASH, (HERE / "top_errors.sh").as_posix(), (self.tmp / name).as_posix(), str(n)],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)                                  # বৈধ JSON হতে হবে

    @unittest.skipUnless(BASH, "bash not installed")
    def test_same_answer_on_normal_log(self) -> None:
        p, s = self.py("access.log", 3), self.sh("access.log", 3)
        self.assertEqual((p["top"], p["total_5xx"]), (s["top"], s["total_5xx"]))
        self.assertEqual(p["unparsed_lines"], 0)

    @unittest.skipUnless(BASH, "bash not installed")
    def test_bash_silently_misses_unencoded_space(self) -> None:
        p, s = self.py("tricky.log"), self.sh("tricky.log")
        self.assertEqual(p["total_5xx"], 5)
        self.assertEqual(s["total_5xx"], 4)                          # 502-টি হারিয়েছে — কোনো সতর্কতা ছাড়া
        self.assertIn("/my file.txt", [t["path"] for t in p["top"]])
        self.assertNotIn("/my file.txt", [t["path"] for t in s["top"]])

    def test_python_reports_unparsed_and_unescapes(self) -> None:
        p = self.py("tricky.log")
        self.assertEqual(p["unparsed_lines"], 1)                     # কাটা লাইন গোনা হয়, লুকানো নয়
        paths = [t["path"] for t in p["top"]]
        self.assertIn('/search?q="rm"', paths)
        self.assertIn("/a\\b", paths)
        self.assertIn("/খোঁজ", paths)

    def test_usage(self) -> None:
        self.assertEqual(te.main([]), 2)
        self.assertEqual(te.main([str(self.tmp / "access.log"), "x"]), 2)
        self.assertEqual(te.main([str(self.tmp / "missing.log")]), 2)


if __name__ == "__main__":
    unittest.main()
