"""Tests for zone_lint.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import zone_lint as zl  # noqa: E402

HEAD = "$ORIGIN example.org.\n$TTL 1h\n@ IN SOA ns1 host ( 1 2 3 4 5 )\n@ IN NS ns1.example.net.\n@ IN CAA 0 issue \"letsencrypt.org\"\n"


def codes(body: str) -> list[str]:
    records, findings = zl.parse(HEAD + body)
    return sorted(f.code for f in findings + zl.lint(records, "example.org."))


class ParseTest(unittest.TestCase):
    def test_names_ttls_and_continuation(self) -> None:
        records, findings = zl.parse(HEAD + "www 5m IN A 203.0.113.5\n    IN AAAA 2001:db8::5\n")
        self.assertEqual(findings, [])
        soa = records[0]
        self.assertEqual((soa.name, soa.ttl, len(soa.rdata)), ("example.org.", 3600, 7))   # multi-line SOA
        www = [r for r in records if r.name == "www.example.org."]
        self.assertEqual([(r.type, r.ttl) for r in www], [("A", 300), ("AAAA", 3600)])  # খালি column = আগের নাম

    def test_semicolon_inside_quotes_is_not_comment(self) -> None:
        records, _ = zl.parse(HEAD + '@ IN TXT "a;b" ; real comment\n')
        self.assertEqual(records[-1].rdata, ("a;b",))


class LintTest(unittest.TestCase):
    def test_clean_zone(self) -> None:
        self.assertEqual(codes("@ IN A 203.0.113.10\nwww IN CNAME example.org.\n"), [])

    def test_each_rule(self) -> None:
        cases = {
            "@ IN CNAME lb.example.net.\n": "cname-at-apex",
            "x IN A 203.0.113.1\nx IN CNAME y.example.net.\n": "cname-and-other-data",
            "app IN CNAME app.example.org\n": "missing-trailing-dot",
            "m IN CNAME mx.example.net.\n@ IN MX 10 m.example.org.\n": "target-is-cname",
            '@ IN TXT "v=spf1 -all"\n@ IN TXT "v=spf1 ~all"\n': "multiple-spf",
            "i IN A 10.1.2.3\n": "private-ip",
            "c 20 IN A 203.0.113.9\n": "ttl-very-low",
            "a 60 IN A 203.0.113.1\na 300 IN A 203.0.113.2\n": "mixed-ttl",
            "b IN A 999.1.1.1\n": "bad-a",
        }
        for body, code in cases.items():
            with self.subTest(code=code):
                self.assertIn(code, codes(body))

    def test_documentation_range_is_not_private(self) -> None:
        # ipaddress.is_private 192.0.2.0/24-কে True বলে — সেই ভুল আর নেই
        self.assertNotIn("private-ip", codes("d IN A 192.0.2.10\n"))

    def test_missing_caa_and_ns(self) -> None:
        records, _ = zl.parse("$ORIGIN example.org.\n$TTL 300\n@ IN A 203.0.113.1\n")
        self.assertEqual(sorted(f.code for f in zl.lint(records, "example.org.")), ["no-caa", "no-ns"])

    def test_sample_zone(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            code = zl.main([str(HERE / "example-zone.txt")])
        self.assertEqual(code, 1)
        self.assertIn("6 error(s)", out.getvalue())


class PlanTest(unittest.TestCase):
    def test_timeline(self) -> None:
        steps = zl.plan(86400, 300, datetime(2026, 11, 3, 2, tzinfo=UTC))
        self.assertEqual(steps[0][0], datetime(2026, 11, 2, 1, tzinfo=UTC))       # পুরোনো TTL + ১ ঘণ্টা আগে
        self.assertEqual(steps[3][0], datetime(2026, 11, 4, 2, tzinfo=UTC))


if __name__ == "__main__":
    unittest.main()
