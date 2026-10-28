"""Tests for server_select.py — চালানো: python3 -m unittest -v

প্রত্যাশিত ফলগুলো nginx documentation-এর নিজস্ব উদাহরণ থেকে নেওয়া (link test-এর পাশে)।
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import server_select as ss  # noqa: E402

nc = ss.nc


def servers(text: str) -> list[ss.Server]:
    return ss.servers_of(nc.parse(text))


class ServerNameTest(unittest.TestCase):
    # https://nginx.org/en/docs/http/server_names.html — exact → longest *. → longest .* → first regex
    CONF = """
      server { listen 80; server_name _; }
      server { listen 80; server_name ~^www\\..+\\.example\\.org$; }
      server { listen 80; server_name *.example.org; }
      server { listen 80; server_name *.www.example.org; }
      server { listen 80; server_name mail.*; }
      server { listen 80; server_name www.example.org; }
      server { listen 80 default_server; server_name default.example; }
    """

    def pick(self, host: str) -> int:
        return ss.select_server(servers(self.CONF), host, 80)[0].index

    def test_precedence(self) -> None:
        self.assertEqual(self.pick("www.example.org"), 5)          # exact জেতে, regex আগে থাকলেও
        self.assertEqual(self.pick("a.www.example.org"), 3)        # দীর্ঘতম leading wildcard
        self.assertEqual(self.pick("x.example.org"), 2)
        self.assertEqual(self.pick("mail.example.com"), 4)         # trailing wildcard
        self.assertEqual(self.pick("www.foo.example.org"), 2)      # *.www… মেলে না; *.example.org regex-এর আগে

    def test_default_server_and_normalisation(self) -> None:
        self.assertEqual(self.pick("203.0.113.9"), 6)              # কিছু মেলেনি → default_server, প্রথম নয়
        self.assertEqual(self.pick("WWW.Example.ORG.:80"), 5)      # case, শেষের dot, port বাদ
        no_default = servers("server { listen 80; server_name a.test; } server { listen 80; server_name b.test; }")
        self.assertEqual(ss.select_server(no_default, "zzz", 80)[0].index, 0)

    def test_dot_prefix_and_listen_ports(self) -> None:
        conf = servers("server { listen 8080; server_name .example.com; } server { listen 80; server_name example.com; }")
        self.assertEqual(ss.select_server(conf, "example.com", 8080)[0].index, 0)
        self.assertEqual(ss.select_server(conf, "a.b.example.com", 8080)[0].index, 0)
        self.assertEqual(ss.select_server(conf, "example.com", 80)[0].index, 1)
        with self.assertRaises(LookupError):
            ss.select_server(conf, "example.com", 443)

    def test_pcre_named_group(self) -> None:
        self.assertEqual(ss.pcre("^(?<user>.+)\\.example\\.net$"), "^(?P<user>.+)\\.example\\.net$")
        self.assertEqual(ss.pcre("(?<=a)b(?<!c)"), "(?<=a)b(?<!c)")                     # lookbehind অপরিবর্তিত
        conf = servers("server { listen 80; server_name ~^(?<env>dev|staging)\\.example\\.net$; }"
                       "server { listen 80 default_server; server_name _; }")
        self.assertEqual(ss.select_server(conf, "staging.example.net", 80)[0].index, 0)

    def test_parse_listen(self) -> None:
        self.assertEqual(ss.parse_listen(["[::]:443", "ssl", "default_server"]), ss.Listen("::", 443, True))
        self.assertEqual(ss.parse_listen(["127.0.0.1:8080"]), ss.Listen("127.0.0.1", 8080, False))
        self.assertEqual(ss.parse_listen(["0.0.0.0:80"]), ss.Listen("*", 80, False))


class LocationTest(unittest.TestCase):
    # https://nginx.org/en/docs/http/ngx_http_core_module.html#location — documentation-এর A–E উদাহরণ
    CONF = """server { listen 80;
        location = / { return 200 A; }
        location / { return 200 B; }
        location /documents/ { return 200 C; }
        location ^~ /images/ { return 200 D; }
        location ~* \\.(gif|jpg|jpeg)$ { return 200 E; }
    }"""

    def test_documentation_example(self) -> None:
        srv = servers(self.CONF)[0]
        expected = {"/": "A", "/index.html": "B", "/documents/document.html": "C",
                    "/images/1.gif": "D", "/documents/1.jpg": "E", "/?a=1": "A"}
        for uri, letter in expected.items():
            with self.subTest(uri=uri):
                loc, _ = ss.select_location(srv, uri)
                self.assertEqual(loc.first("return").args[1], letter)

    def test_first_regex_in_config_order_wins(self) -> None:
        srv = servers("server { location ~ \\.php$ { return 200 first; } location ~ ^/admin { return 200 second; } }")[0]
        loc, why = ss.select_location(srv, "/admin/index.php")
        self.assertEqual((loc.first("return").args[1], why), ("first", "first matching regex (~)"))


class CliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(ss.main([str(HERE / "sites.conf"), *args]), 0)
        return out.getvalue()

    def test_sample_sites(self) -> None:
        self.assertIn("default_server", self.run_cli("--host", "198.51.100.7"))
        self.assertIn("deny all", self.run_cli("--host", "example.com", "--uri", "/.env"))
        self.assertIn("server-level return", self.run_cli("--host", "shop.example.com"))
        self.assertIn("^~", self.run_cli("--host", "example.com", "--uri", "/static/logo.png"))


if __name__ == "__main__":
    unittest.main()
