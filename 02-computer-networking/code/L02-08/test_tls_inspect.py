"""Tests for tls_inspect.py — চালানো: python3 -m unittest -v

openssl CLI দিয়ে temporary directory-তে CA ও certificate তৈরি করে loopback-এ TLS server।
openssl না থাকলে lab-ভিত্তিক test skip হয়। কোনো key repository-তে লেখা হয় না।
"""
from __future__ import annotations

import ssl
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import tls_inspect as ti  # noqa: E402


class PureTest(unittest.TestCase):
    def test_days_left(self) -> None:
        now = ssl.cert_time_to_seconds("Jan  1 00:00:00 2027 GMT")
        self.assertAlmostEqual(ti.days_left("Jan 11 00:00:00 2027 GMT", now), 10.0)
        self.assertLess(ti.days_left("Dec 31 00:00:00 2026 GMT", now), 0)   # মেয়াদ শেষ

    def test_name_format(self) -> None:
        rdns = ((("countryName", "BD"),), (("commonName", "example.com"),))
        self.assertEqual(ti._name(rdns), "countryName=BD, commonName=example.com")

    def test_client_context_is_strict(self) -> None:
        ctx = ti.client_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)


@unittest.skipUnless(ti.openssl_bin(), "openssl CLI not installed")
class LabTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(prefix="tls-test-")
        cls.p = ti.make_ca_and_leaf(Path(cls.tmp.name), days=10)
        cls.srv, cls.port, cls.stop = ti.start_tls_server(cls.p["leaf.crt"], cls.p["leaf.key"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.stop.set()
        cls.srv.close()
        cls.tmp.cleanup()

    def test_verified_ok(self) -> None:
        info = ti.inspect("127.0.0.1", self.port, str(self.p["ca.crt"]), "localhost")
        self.assertIn("commonName=localhost", info.subject)
        self.assertIn("commonName=Lab Root CA", info.issuer)
        self.assertIn("DNS:localhost", info.san)
        self.assertIn(info.version, ("TLSv1.2", "TLSv1.3"))
        self.assertTrue(9 < info.days_left <= 10)

    def test_ip_san_ok(self) -> None:
        info = ti.inspect("127.0.0.1", self.port, str(self.p["ca.crt"]))      # name = 127.0.0.1 → IP SAN
        self.assertIn("IP Address:127.0.0.1", info.san)

    def test_hostname_mismatch(self) -> None:
        with self.assertRaises(ssl.SSLCertVerificationError) as cm:
            ti.inspect("127.0.0.1", self.port, str(self.p["ca.crt"]), "api.example.com")
        self.assertIn("mismatch", cm.exception.verify_message.lower())

    def test_untrusted_ca(self) -> None:
        with self.assertRaises(ssl.SSLCertVerificationError):
            ti.inspect("127.0.0.1", self.port, None, "localhost")

    def test_cli_warn_days(self) -> None:
        base = ["inspect", "127.0.0.1", "--port", str(self.port), "--cafile", str(self.p["ca.crt"]),
                "--server-name", "localhost"]
        self.assertEqual(ti.main(base + ["--warn-days", "5"]), 0)
        self.assertEqual(ti.main(base + ["--warn-days", "30"]), 1)            # ১০ দিন < ৩০
        self.assertEqual(ti.main(base[:-2] + ["--server-name", "wrong.example"]), 1)


if __name__ == "__main__":
    unittest.main()
