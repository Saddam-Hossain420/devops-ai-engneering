"""Tests for unit_lint.py and hello_service.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hello_service as hs  # noqa: E402
import unit_lint as ul  # noqa: E402

BAD_UNIT = """
[Service]
ExecStart=python3 app.py
Environment=A=1
Environment=B=2
"""


class ParseTest(unittest.TestCase):
    def test_repeated_keys_and_continuation(self) -> None:
        u = ul.parse_unit("[Service]\nEnvironment=A=1\nEnvironment=B=2\nExecStart=/usr/bin/python3 \\\n  app.py\n")
        self.assertEqual(u["Service"]["Environment"], ["A=1", "B=2"])
        self.assertEqual(u["Service"]["ExecStart"], ["/usr/bin/python3 app.py"])

    def test_invalid(self) -> None:
        with self.assertRaises(ValueError):
            ul.parse_unit("ExecStart=/bin/true\n")   # section ছাড়া


class LintTest(unittest.TestCase):
    def test_good_unit_has_no_warnings(self) -> None:
        findings = ul.lint((HERE / "taskflow-demo.service").read_text(encoding="utf-8"))
        self.assertEqual(findings, [])

    def test_bad_unit(self) -> None:
        text = "\n".join(f"{lvl} {msg}" for lvl, msg in ul.lint(BAD_UNIT))
        self.assertIn("WARN [Unit] Description missing", text)
        self.assertIn("relative program 'python3'", text)
        self.assertIn("no User=", text)
        self.assertIn("Restart= not set", text)
        self.assertIn("WantedBy missing", text)
        self.assertIn("INFO consider NoNewPrivileges=", text)

    def test_shell_wrapper(self) -> None:
        unit = "[Unit]\nDescription=x\n[Service]\nUser=app\nRestart=on-failure\n" \
               "ExecStart=/bin/bash -c 'cd /app && python3 run.py'\n[Install]\nWantedBy=multi-user.target\n"
        self.assertTrue(any("shell wrapper" in m for _, m in ul.lint(unit)))
        fixed = unit.replace("&& python3", "&& exec python3")
        self.assertFalse(any("shell wrapper" in m for _, m in ul.lint(fixed)))

    def test_cli(self) -> None:
        self.assertEqual(ul.main([str(HERE / "taskflow-demo.service")]), 0)
        self.assertEqual(ul.main([str(HERE / "missing.service")]), 2)


class ServiceTest(unittest.TestCase):
    def test_health_and_404(self) -> None:
        server = hs.build_server("127.0.0.1", 0)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                self.assertEqual((r.status, r.read()), (200, b"ok\n"))
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=5)
            self.assertEqual(ctx.exception.code, 404)
            ctx.exception.close()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
