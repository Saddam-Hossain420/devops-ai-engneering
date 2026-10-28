"""Tests for nginx_conf.py ও event_loop_demo.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import event_loop_demo as ev  # noqa: E402
import nginx_conf as nc  # noqa: E402


class ParserTest(unittest.TestCase):
    def test_sample_with_include(self) -> None:
        tree = nc.load(HERE / "sample-nginx.conf")
        found = [(ctx, d.args) for ctx, d in nc.walk(tree) if d.name == "proxy_pass"]
        self.assertEqual(found, [(("http", "server", "location"), ["http://127.0.0.1:8000"])])
        self.assertEqual(tree[0].name, "user")

    def test_quotes_comments_and_regex(self) -> None:
        tree = nc.parse('add_header X "a;b # c"; # comment\nlocation ~ ^/api/(v\\d+)$ { return 200 "{}"; }')
        self.assertEqual(tree[0].args, ["X", "a;b # c"])
        loc = tree[1]
        self.assertEqual(loc.args, ["~", "^/api/(v\\d+)$"])
        self.assertEqual(loc.first("return").args, ["200", "{}"])                 # quote-এর ভেতরের { } block নয়

    def test_errors_like_nginx(self) -> None:
        cases = {"events { worker_connections 10 }": "not terminated by ';'",
                 "http { server { }": "expecting '}'", "}": "unexpected '}'", 'a "b;': "unterminated quote",
                 "x 1": "unexpected end of file"}
        for text, message in cases.items():
            with self.subTest(text=text), self.assertRaisesRegex(nc.ConfError, message):
                nc.parse(text)

    def test_include_glob_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "main.conf").write_text("include sites/*.conf;\ninclude none/*.conf;\n", encoding="utf-8")
            (base / "sites").mkdir()
            (base / "sites" / "a.conf").write_text("server { listen 80; }\n", encoding="utf-8")
            self.assertEqual([d.name for d in nc.load(base / "main.conf")], ["server"])  # খালি glob = error নয়
            (base / "bad.conf").write_text("include missing.conf;\n", encoding="utf-8")
            with self.assertRaisesRegex(nc.ConfError, "not found"):
                nc.load(base / "bad.conf")


class CapacityTest(unittest.TestCase):
    def test_fd_limit_caps_connections(self) -> None:
        cap = nc.capacity(nc.load(HERE / "sample-nginx.conf"), cpus=4, nofile=1024)
        self.assertEqual((cap["workers"], cap["max_connections"], cap["max_clients_estimate"]), (4, 4096, 2048))
        self.assertTrue(cap["notes"])
        cap = nc.capacity(nc.parse("worker_processes 2; worker_rlimit_nofile 65535; events { worker_connections 4096; }"),
                          cpus=8, nofile=1024, proxied=False)
        self.assertEqual((cap["max_connections"], cap["max_clients_estimate"], cap["notes"]), (8192, 8192, []))

    def test_cli(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(nc.main(["get", str(HERE / "sample-nginx.conf"), "worker_connections"]), 0)
        self.assertIn("events: worker_connections 4096", out.getvalue())


class EventLoopTest(unittest.TestCase):
    def test_slow_clients_block_thread_pool_but_not_event_loop(self) -> None:
        event_time, _ = ev.run("event", slow=6, workers=6, header_timeout=1.5)
        threaded_time, _ = ev.run("threaded", slow=6, workers=6, header_timeout=1.5)
        self.assertLess(event_time, 0.5)
        self.assertGreater(threaded_time, 1.0)                                    # সব worker ধীর client-এ আটকে

    def test_one_free_worker_is_enough(self) -> None:
        took, _ = ev.run("threaded", slow=5, workers=6, header_timeout=1.5)
        self.assertLess(took, 0.5)


if __name__ == "__main__":
    unittest.main()
