"""Tests for inventory.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import dataclasses
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import inventory as inv  # noqa: E402

HEADER = "name,ip,env,role,cpu,mem_gb,tags\n"


class ParseTest(unittest.TestCase):
    def test_valid_row(self) -> None:
        h = inv.parse_row({"name": "a", "ip": "192.0.2.1", "env": "prod", "role": "web",
                           "cpu": "2", "mem_gb": "4", "tags": "x;y"})
        self.assertIs(h.env, inv.Env.PROD)
        self.assertEqual(h.tags, ("x", "y"))
        self.assertTrue(h.is_prod)

    def test_invalid_rows(self) -> None:
        base = {"name": "a", "ip": "192.0.2.1", "env": "prod", "role": "web", "cpu": "2", "mem_gb": "4"}
        for bad, needle in [({"ip": "192.0.2.300"}, "invalid ip"), ({"env": "qa"}, "unknown env"),
                            ({"cpu": "two"}, "integers"), ({"mem_gb": "0"}, "positive"),
                            ({"name": " "}, "name")]:
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, needle):
                inv.parse_row({**base, **bad})

    def test_frozen(self) -> None:
        h = inv.parse_row({"name": "a", "ip": "::1", "env": "dev", "role": "db", "cpu": "1", "mem_gb": "1"})
        with self.assertRaises(dataclasses.FrozenInstanceError):
            h.cpu = 8  # type: ignore[misc]

    def test_strenum_str(self) -> None:
        self.assertEqual(str(inv.Env.PROD), "prod")          # StrEnum — argparse help-এ এটাই দেখায়
        self.assertEqual(inv.Env("prod"), "prod")


class LoadTest(unittest.TestCase):
    def test_sample_file(self) -> None:
        hosts, problems = inv.load((HERE / "hosts.csv").read_text(encoding="utf-8"))
        self.assertEqual(len(hosts), 6)
        self.assertEqual([p.line for p in problems], [9, 10])   # comment লাইন গোনা হয়েছে
        self.assertIn("duplicate", problems[0].message)

    def test_multiline_quoted_field_keeps_line_numbers(self) -> None:
        text = HEADER + 'a,192.0.2.1,dev,web,1,1,"x\ny"\nb,bad-ip,dev,web,1,1,\n'
        hosts, problems = inv.load(text)
        self.assertEqual(hosts[0].tags, ("x\ny",))
        self.assertEqual(problems[0].line, 4)

    def test_select_and_group(self) -> None:
        hosts, _ = inv.load((HERE / "hosts.csv").read_text(encoding="utf-8"))
        self.assertEqual([h.name for h in inv.select(hosts, inv.Env.PROD, inv.Role.WEB)], ["web-01", "web-02"])
        self.assertEqual(list(inv.group_by(hosts, "env")), ["dev", "prod", "staging"])


class CliTest(unittest.TestCase):
    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = inv.main(list(args))
            except SystemExit as exc:
                code = int(exc.code or 0)
        return code, out.getvalue(), err.getvalue()

    def test_exit_codes_and_json(self) -> None:
        code, out, _ = self.run_main(str(HERE / "hosts.csv"), "--env", "staging", "--json")
        self.assertEqual(code, 1)
        self.assertEqual([h["name"] for h in json.loads(out)["hosts"]], ["web-stg-01", "db-stg-01"])
        self.assertEqual(self.run_main(str(HERE / "missing.csv"))[0], 2)
        self.assertEqual(self.run_main(str(HERE / "hosts.csv"), "--env", "qa")[0], 2)


if __name__ == "__main__":
    unittest.main()
