"""Tests for proxy_uri.py, proxy_lint.py, error_explainer.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import error_explainer as ee  # noqa: E402
import proxy_lint as pl  # noqa: E402
import proxy_uri as pu  # noqa: E402

nc = pl.nc


class ProxyUriTest(unittest.TestCase):
    def test_documentation_example(self) -> None:
        # nginx doc: location /name/ { proxy_pass http://127.0.0.1/remote/; } — /name/ → /remote/
        self.assertEqual(pu.upstream_uri("/name/", "http://127.0.0.1/remote/", "/name/x/y"), "/remote/x/y")
        self.assertEqual(pu.upstream_uri("/some/path/", "http://127.0.0.1", "/some/path/page.html"),
                         "/some/path/page.html")                                     # URI অংশ নেই → অপরিবর্তিত

    def test_slash_traps(self) -> None:
        self.assertEqual(pu.upstream_uri("/api", "http://app:8000/", "/api/tasks"), "//tasks")
        self.assertEqual(pu.upstream_uri("/api/", "http://app:8000/v1", "/api/tasks"), "/v1tasks")
        self.assertEqual(pu.upstream_uri("/api", "http://app:8000/v1/", "/apiary"), "/v1/ary")
        self.assertEqual(pu.upstream_uri("/api/", "http://app:8000/v1/", "/api/t?done=true"), "/v1/t?done=true")

    def test_regex_and_variables(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot have URI part"):
            pu.upstream_uri("~ ^/api", "http://app/", "/api/x", regex_location=True)
        self.assertEqual(pu.upstream_uri("~ ^/api", "http://app", "/api/x", regex_location=True), "/api/x")
        self.assertEqual(pu.upstream_uri("/api/", "http://$backend", "/api/x?a=1"), "/api/x?a=1")


class ProxyLintTest(unittest.TestCase):
    def codes(self, text: str) -> list[str]:
        return sorted(f.code for f in pl.lint(nc.parse(text)))

    def test_broken_sample(self) -> None:
        found = {f.code for f in pl.lint(nc.load(HERE / "taskflow-broken.conf"))}
        self.assertEqual(found, {"localhost-upstream", "keepalive-unused", "proxy-header-inheritance",
                                 "missing-forward-headers", "timeout-too-long", "default-body-size"})

    def test_good_sample_is_clean(self) -> None:
        self.assertEqual(pl.lint(nc.load(HERE / "taskflow.conf")), [])

    def test_inheritance_detected(self) -> None:
        conf = ('client_max_body_size 1m; server { proxy_set_header Host $host; '
                'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme;'
                ' location / { proxy_pass http://127.0.0.1:8000; } '
                ' location /x { proxy_set_header X-Extra 1; proxy_pass http://127.0.0.1:8000; } }')
        self.assertEqual(self.codes(conf), ["missing-forward-headers", "proxy-header-inheritance"])

    def test_keepalive_rule(self) -> None:
        base = ('client_max_body_size 1m; upstream u { server 127.0.0.1:1; keepalive 4; } server { location / {'
                ' proxy_set_header Host $host; proxy_set_header X-Forwarded-For x; proxy_set_header X-Forwarded-Proto y;'
                ' proxy_pass http://u; %s } }')
        self.assertIn("keepalive-unused", self.codes(base % ""))
        self.assertEqual(self.codes(base % 'proxy_http_version 1.1; proxy_set_header Connection "";'), [])


class ExplainerTest(unittest.TestCase):
    def test_sample_log(self) -> None:
        lines = (HERE / "sample-error.log").read_text(encoding="utf-8").splitlines()
        statuses = [e.status if (e := ee.explain(line)) else None for line in lines]
        self.assertEqual(statuses, ["502", "502", "502", "504", "413", "502", "502", None])
        first = ee.explain(lines[0])
        assert first is not None
        self.assertEqual((first.request, first.upstream), ("GET /tasks HTTP/1.1", "http://127.0.0.1:8000/tasks"))

    def test_connect_vs_read_timeout(self) -> None:
        connect = ee.explain("upstream timed out (110: Connection timed out) while connecting to upstream, client: x")
        read = ee.explain("upstream timed out (110: Connection timed out) while reading response header from upstream")
        assert connect and read
        self.assertIn("TCP connect", connect.cause)
        self.assertIn("slower than proxy_read_timeout", read.cause)


if __name__ == "__main__":
    unittest.main()
