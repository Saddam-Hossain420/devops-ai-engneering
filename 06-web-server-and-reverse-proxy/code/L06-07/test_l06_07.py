"""Tests for pki_lab.py, cert_expiry.py, tls_conf_lint.py — চালানো: python3 -m unittest -v

openssl CLI না থাকলে PKI-নির্ভর test skip হয়। সব key temp directory-তে, শেষে মুছে যায়।
"""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cert_expiry as ce  # noqa: E402
import pki_lab as pk  # noqa: E402
import tls_conf_lint as tl  # noqa: E402

HAS_OPENSSL = shutil.which("openssl") is not None


@unittest.skipUnless(HAS_OPENSSL, "openssl CLI needed")
class PkiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.results = dict(pk.scenarios(Path(cls._tmp.name)))
        cls.files = {p.name: p for p in Path(cls._tmp.name).iterdir()}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_five_scenarios(self) -> None:
        r = self.results
        self.assertTrue(r["fullchain (leaf + intermediate)"].startswith("OK TLSv1."))
        self.assertIn("unable to get local issuer certificate", r["leaf only — intermediate missing"])
        self.assertIn("certificate has expired", r["expired leaf"])
        self.assertIn("KEY_VALUES_MISMATCH", r["wrong order (intermediate first)"])
        self.assertIn("KEY_VALUES_MISMATCH", r["key does not match certificate"])

    def test_wrong_hostname(self) -> None:
        started = pk.serve_once(self.files["fullchain.pem"], self.files["server.key"])
        assert not isinstance(started, str)
        port, t = started
        self.assertIn("Hostname mismatch", pk.client(port, self.files["root.crt"], name="other.example.com"))
        t.join(timeout=5)

    def test_expiry_from_files(self) -> None:
        na = ce.not_after_from_file(str(self.files["expired.crt"]))
        self.assertEqual(na, datetime(2025, 2, 1, tzinfo=UTC))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ce.main([str(self.files["server.crt"]), "--warn-days", "1", "--crit-days", "0"]), ce.OK)
            self.assertEqual(ce.main([str(self.files["expired.crt"])]), ce.CRITICAL)
            self.assertEqual(ce.main([str(self.files["server.key"])]), ce.UNKNOWN)      # cert নয়


class ClassifyTest(unittest.TestCase):
    def test_thresholds(self) -> None:
        now = datetime(2026, 10, 27, tzinfo=UTC)
        self.assertEqual(ce.classify(now + timedelta(days=30), 21, 7, now)[0], ce.OK)
        self.assertEqual(ce.classify(now + timedelta(days=10), 21, 7, now)[0], ce.WARNING)
        self.assertEqual(ce.classify(now + timedelta(days=3), 21, 7, now)[0], ce.CRITICAL)
        self.assertEqual(ce.classify(now - timedelta(days=1), 21, 7, now)[0], ce.CRITICAL)


class TlsLintTest(unittest.TestCase):
    def codes(self, path: Path) -> set[str]:
        return {f[2] for f in tl.lint(tl.nc.load(path))}

    def test_broken_sample(self) -> None:
        self.assertEqual(self.codes(HERE / "taskflow-tls-broken.conf"),
                         {"maybe-no-chain", "key-location", "old-protocol", "weak-cipher", "server-tokens",
                          "hsts-not-always", "no-https-redirect"})

    def test_good_sample_is_clean(self) -> None:
        # regression: redirect location-এর ভেতরে থাকলেও চেনা উচিত
        self.assertEqual(self.codes(HERE / "taskflow-tls.conf"), set())

    def test_negated_weak_ciphers_are_fine(self) -> None:
        tree = tl.nc.parse('server { listen 443 ssl; ssl_certificate fullchain.pem; ssl_ciphers "HIGH:!RC4:!3DES:!NULL";'
                           ' add_header Strict-Transport-Security "max-age=1" always; }')
        self.assertEqual({f[2] for f in tl.lint(tree)}, set())


if __name__ == "__main__":
    unittest.main()
