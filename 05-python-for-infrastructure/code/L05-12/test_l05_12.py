"""Tests for healthcheck.py ও verify_backup.py — চালানো: python3 -m unittest -v

HTTP check-এর জন্য 127.0.0.1-এ local server; backup-এর জন্য make_demo_backups.py temp directory-তে।
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import healthcheck as hc  # noqa: E402
import verify_backup as vb  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/slow":
            time.sleep(6)
        body = b'{"status": "degraded"}' if self.path == "/degraded" else b'{"status": "ok"}'
        self.send_response(404 if self.path == "/missing" else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class HealthcheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.srv.shutdown()
        cls.srv.server_close()

    def http(self, name: str, path: str, **kw: object) -> dict[str, object]:
        return {"name": name, "type": "http", "url": self.base + path, "timeout": 3, **kw}

    def test_http_variants(self) -> None:
        results = hc.run_all([self.http("ok", "/health", contains='"ok"'),
                              self.http("degraded", "/degraded", contains='"ok"'),
                              self.http("missing", "/missing")], deadline=10)
        self.assertEqual([r.status for r in results], [hc.OK, hc.CRITICAL, hc.CRITICAL])
        self.assertIn("lacks", results[1].detail)
        self.assertIn("HTTP 404", results[2].detail)

    def test_tcp_disk_file_age(self) -> None:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            closed = s.getsockname()[1]
        with tempfile.NamedTemporaryFile(delete=False) as f:
            old = Path(f.name)
        os.utime(old, (time.time() - 30 * 3600, time.time() - 30 * 3600))
        try:
            results = hc.run_all([
                {"name": "tcp", "type": "tcp", "host": "127.0.0.1", "port": closed, "timeout": 3},
                {"name": "disk", "type": "disk", "path": str(HERE), "warn": 0.0, "crit": 100.1},
                {"name": "age", "type": "file_age", "path": str(old), "warn_h": 26, "crit_h": 50},
                {"name": "gone", "type": "file_age", "path": str(old) + ".missing"},
            ], deadline=10)
        finally:
            old.unlink()
        self.assertEqual([r.status for r in results], [hc.CRITICAL, hc.WARNING, hc.WARNING, hc.CRITICAL])

    def test_config_validation(self) -> None:
        self.assertEqual(hc.validate({"a": 1}), ["config must be a JSON list of checks"])
        errors = hc.validate([{"name": "a", "type": "http"}, {"name": "a", "type": "ftp"}, {"type": "tcp", "host": "h"}])
        self.assertIn("a: missing 'url'", errors)
        self.assertTrue(any("duplicate name 'a'" in e for e in errors))
        self.assertTrue(any("unknown type 'ftp'" in e for e in errors))

    def test_deadline_is_honoured_by_the_process(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d, "c.json")
            cfg.write_text(json.dumps([self.http("slow", "/slow", timeout=30),
                                       {"name": "disk", "type": "disk", "path": "."}]), encoding="utf-8")
            start = time.monotonic()
            proc = subprocess.run([sys.executable, str(HERE / "healthcheck.py"), str(cfg), "--deadline", "1", "--json"],
                                  capture_output=True, text=True, timeout=60)
            wall = time.monotonic() - start
        self.assertLess(wall, 4.5)                          # ThreadPoolExecutor-এ ~৬ s লাগত (exit-এ join)
        doc = json.loads(proc.stdout)
        self.assertEqual((proc.returncode, doc["checks"][0]["status"]), (hc.UNKNOWN, "unknown"))


class VerifyBackupTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls._tmp.name)
        subprocess.run([sys.executable, str(HERE / "make_demo_backups.py"), str(cls.dir)],
                       check=True, capture_output=True, timeout=60)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def failed(self, prefix: str) -> list[str]:
        (path,) = self.dir.glob(f"{prefix}-*.tar.gz")
        return [s.name for s in vb.verify(path, 26, 1000, ["taskflow.db"], "taskflow.db") if not s.ok]

    def test_each_demo_backup(self) -> None:
        expected = {
            "01-good": [],
            "02-truncated": ["size", "checksum", "archive", "contents", "restore"],
            "03-bitflip": ["checksum", "archive", "contents", "restore"],
            "04-traversal": ["archive", "contents", "restore"],        # checksum PASS — checksum নিরাপত্তা নয়
            "05-missing-db": ["size", "contents", "sqlite"],
            "06-stale": ["age"],
            "07-corrupt-db": ["sqlite"],                               # শুধু আসল restore + DB check ধরে
        }
        for prefix, want in expected.items():
            with self.subTest(prefix=prefix):
                self.assertEqual(self.failed(prefix), want)

    def test_bit_flip_in_data_is_caught_by_gzip_crc(self) -> None:
        # regression: tarfile gzip-এর শেষের CRC পর্যন্ত পড়ে না — data-র মাঝের flip নীরবে চলে যাচ্ছিল।
        # compresslevel 0 (stored block): flip অবশ্যই literal data-তে পড়ে, zlib-এর কাঠামোয় নয় — শুধু CRC ধরতে পারে।
        import gzip
        import io
        import tarfile
        with tempfile.TemporaryDirectory() as d:
            raw = io.BytesIO()
            with tarfile.open(fileobj=raw, mode="w") as tar:
                data = b"x" * 20000
                info = tarfile.TarInfo("data.bin")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            blob = bytearray(gzip.compress(raw.getvalue(), compresslevel=0, mtime=0))
            blob[len(blob) // 3] ^= 0x01
            path = Path(d, "flip-20261027T0000Z.tar.gz")
            path.write_bytes(bytes(blob))
            step, _ = vb.check_archive(path)
        self.assertFalse(step.ok)
        self.assertIn("CRC", step.detail)

    def test_traversal_never_writes_outside(self) -> None:
        (path,) = self.dir.glob("04-traversal-*.tar.gz")
        vb.verify(path, 26, 1, [], None)
        self.assertFalse((self.dir.parent / "outside.txt").exists())

    def test_unsafe_names(self) -> None:
        for name in ("../x", "a/../../x", "/etc/passwd", "C:evil", "\\\\server\\x", ""):
            with self.subTest(name=name):
                self.assertTrue(vb.unsafe_member(name))
        self.assertFalse(vb.unsafe_member("config/app.toml"))

    def test_missing_checksum_and_cli(self) -> None:
        (good,) = self.dir.glob("01-good-*.tar.gz")
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d, good.name)
            copy.write_bytes(good.read_bytes())
            steps = {s.name: s.ok for s in vb.verify(copy, 26, 1, [], None)}
        self.assertFalse(steps["checksum"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vb.main([str(self.dir / "nope.tar.gz"), "--json"]), 2)


if __name__ == "__main__":
    unittest.main()
