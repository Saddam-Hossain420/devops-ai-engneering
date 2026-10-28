"""Tests for logsetup.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import contextvars
import io
import json
import logging
import subprocess
import sys
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import logsetup as ls  # noqa: E402


class Base(unittest.TestCase):
    def make(self, json_output: bool = True, level: str = "info") -> tuple[logging.Logger, io.StringIO]:
        buf = io.StringIO()
        return ls.setup_logging(level, json_output=json_output, stream=buf, name="t"), buf

    def lines(self, buf: io.StringIO) -> list[dict[str, object]]:
        return [json.loads(line) for line in buf.getvalue().splitlines()]


class JsonTest(Base):
    def test_one_json_object_per_line(self) -> None:
        log, buf = self.make()
        log.info("hello %s", "world", extra={"db": "orders", "size_mb": 120})
        (doc,) = self.lines(buf)
        self.assertEqual((doc["msg"], doc["level"], doc["db"], doc["size_mb"]), ("hello world", "info", "orders", 120))
        self.assertTrue(str(doc["ts"]).endswith("+00:00"))                       # UTC

    def test_exception_is_one_field(self) -> None:
        log, buf = self.make()
        try:
            raise ValueError("bad\nvalue")
        except ValueError:
            log.exception("failed")
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 1)                                          # multi-line traceback তবুও এক লাইন
        doc = json.loads(lines[0])
        self.assertEqual(doc["exc_type"], "ValueError")
        self.assertIn("Traceback", str(doc["exc"]))

    def test_level_and_lazy_formatting(self) -> None:
        log, buf = self.make(level="warning")

        class Expensive:
            calls = 0

            def __str__(self) -> str:
                Expensive.calls += 1
                return "x"

        log.info("value %s", Expensive())
        self.assertEqual((buf.getvalue(), Expensive.calls), ("", 0))           # %-args: বন্ধ level-এ খরচ নেই

    def test_no_duplicate_handlers(self) -> None:
        self.make()
        log, buf = self.make()
        log.info("once")
        self.assertEqual(len(buf.getvalue().splitlines()), 1)


class RedactTest(Base):
    def test_text_patterns(self) -> None:
        cases = {
            "password=hunter2 ok": "password=*** ok",
            'token: "abc def"': "token: ***",
            "Authorization: Bearer eyJhbGciOi.x.y": "Authorization: ***",
            "postgres://app:s3cret@db:5432/x": "postgres://app:***@db:5432/x",
            "API_KEY=AKIA123": "API_KEY=***",
            "keyboard layout": "keyboard layout",
        }
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(ls.redact_text(raw), want)

    def test_extra_fields_and_traceback(self) -> None:
        log, buf = self.make()
        log.info("login", extra={"user": "ana", "password": "x", "headers": {"Authorization": "Bearer y"}})
        try:
            raise ConnectionError("dsn postgres://u:topsecret@h/db")
        except ConnectionError:
            log.exception("db down")
        first, second = self.lines(buf)
        self.assertEqual((first["password"], first["headers"]), ("***", {"Authorization": "***"}))
        self.assertNotIn("topsecret", buf.getvalue())
        self.assertIn("u:***@h", str(second["exc"]))


class ContextTest(Base):
    def test_request_id_and_nesting(self) -> None:
        log, buf = self.make()
        with ls.request_context("outer"):
            log.info("a")
            with ls.request_context("inner"):
                log.info("b")
            log.info("c")
        log.info("d")
        self.assertEqual([d["request_id"] for d in self.lines(buf)], ["outer", "inner", "outer", "-"])

    def test_threads_need_copy_context(self) -> None:
        got: dict[str, str] = {}
        with ls.request_context("req-1"):
            t = threading.Thread(target=lambda: got.__setitem__("plain", ls.request_id.get()))
            t.start()
            t.join()
            ctx = contextvars.copy_context()
            t = threading.Thread(target=ctx.run, args=(lambda: got.__setitem__("copied", ls.request_id.get()),))
            t.start()
            t.join()
        expected_plain = "req-1" if getattr(sys.flags, "thread_inherit_context", 0) else "-"
        self.assertEqual(got, {"plain": expected_plain, "copied": "req-1"})


class TextAndDemoTest(Base):
    def test_text_extras_before_traceback(self) -> None:
        log, buf = self.make(json_output=False)
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            log.exception("failed", extra={"db": "x"})
        first_line = buf.getvalue().splitlines()[0]
        self.assertTrue(first_line.endswith("t: failed db=x"), first_line)

    def test_demo_job_streams(self) -> None:
        r = subprocess.run([sys.executable, str(HERE / "demo_job.py"), "--json"],
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual((r.returncode, r.stdout.strip()), (1, "failed=1"))       # ফল stdout-এ
        docs = [json.loads(line) for line in r.stderr.splitlines()]               # log stderr-এ, সব JSON
        self.assertEqual({d["request_id"] for d in docs}, {"job-7f3a"})           # thread-এর log-ও
        self.assertNotIn("s3cr3t-demo", r.stderr)
        self.assertNotIn("hunter2", r.stderr)


if __name__ == "__main__":
    unittest.main()
