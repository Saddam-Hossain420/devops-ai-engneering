"""Tests for config_loader.py — চালানো: python3 -m unittest -v

YAML-এর test শুধু PyYAML install থাকলে চলে; না থাকলে skip (এবং "স্পষ্ট error" test চলে)।
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import config_loader as cl  # noqa: E402


def write(d: str, name: str, text: str) -> Path:
    p = Path(d, name)
    p.write_text(text, encoding="utf-8")
    return p


class LayeringTest(unittest.TestCase):
    def test_precedence_and_source(self) -> None:
        cfg, src = cl.load(HERE / "app.toml", environ={"APP_SERVER__PORT": "9000", "OTHER": "x"},
                           sets=["server.port=9100", "log.level=debug"])
        self.assertEqual(cfg["server"]["port"], 9100)             # cli > env > file > default
        self.assertEqual(src["server.port"], "cli")
        self.assertEqual((cfg["server"]["host"], src["server.host"]), ("0.0.0.0", "app.toml"))
        self.assertEqual((cfg["server"]["workers"], src["server.workers"]), (2, "default"))
        cfg, src = cl.load(HERE / "app.toml", environ={"APP_SERVER__PORT": "9000"})
        self.assertEqual((cfg["server"]["port"], src["server.port"]), (9000, "env:APP_SERVER__PORT"))
        self.assertEqual(cl.validate(cfg), [])

    def test_defaults_not_mutated(self) -> None:
        cl.load(environ={}, sets=["server.port=1"])
        self.assertEqual(cl.DEFAULTS["server"]["port"], 8080)

    def test_coerce(self) -> None:
        self.assertIs(cl.coerce("off", cl.Rule(bool)), False)
        self.assertEqual(cl.coerce("2.5", cl.Rule(float)), 2.5)
        for raw, rule in [("maybe", cl.Rule(bool)), ("abc", cl.Rule(int))]:
            with self.subTest(raw=raw), self.assertRaises(cl.ConfigError):
                cl.coerce(raw, rule, "x")


class ParseTest(unittest.TestCase):
    def test_duplicate_json_key(self) -> None:
        with self.assertRaisesRegex(cl.ConfigError, "duplicate key 'server'"):
            cl.parse_file(HERE / "dup.json")

    def test_syntax_errors_have_location(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(cl.ConfigError, r"bad\.json:[23]:"):   # 3.13+: comma-র লাইন ২; আগে: ৩
                cl.parse_file(write(d, "bad.json", '{\n  "a": 1,\n}\n'))
            with self.assertRaisesRegex(cl.ConfigError, "line 2"):
                cl.parse_file(write(d, "bad.toml", "[server]\nport = \n"))
            with self.assertRaisesRegex(cl.ConfigError, "top level must be a mapping"):
                cl.parse_file(write(d, "list.json", "[1, 2]"))
            with self.assertRaisesRegex(cl.ConfigError, "unsupported"):
                cl.parse_file(write(d, "x.ini", "a=1"))

    @unittest.skipIf(cl.yaml is not None, "PyYAML installed")
    def test_yaml_without_pyyaml_is_clear_error(self) -> None:
        with self.assertRaisesRegex(cl.ConfigError, "needs PyYAML"):
            cl.parse_file(HERE / "norway.yaml")

    @unittest.skipIf(cl.yaml is None, "PyYAML not installed")
    def test_yaml_norway_problem(self) -> None:
        data = cl.parse_file(HERE / "norway.yaml")
        self.assertEqual(data["countries"][2], False)          # NO → False (YAML 1.1)
        self.assertIs(data["features"]["signup"], True)        # on → True
        self.assertEqual(data["version"], 1.1)                 # 1.10 → float 1.1


class ValidateTest(unittest.TestCase):
    def test_sample_json_problems(self) -> None:
        cfg, _ = cl.load(HERE / "app.json", environ={})
        errors = cl.validate(cfg)
        self.assertIn("featurs.signup: unknown key (typo?)", errors)
        self.assertTrue(any(e.startswith("db.timeout_s: expected float, got str") for e in errors))
        self.assertTrue(any(e.startswith("log.level: 'warn' not in") for e in errors))

    def test_bool_is_not_int_and_int_is_float(self) -> None:
        cfg, _ = cl.load(environ={})
        cfg["server"]["port"] = True
        cfg["db"]["timeout_s"] = 3
        errors = cl.validate(cfg)
        self.assertEqual(errors, ["server.port: expected int, got bool True"])

    def test_required_and_range(self) -> None:
        cfg, _ = cl.load(environ={}, sets=["server.port=70000"])
        cfg["db"]["url"] = None
        self.assertEqual(cl.validate(cfg), ["server.port: 70000 > max 65535", "db.url: required"])

    def test_masking(self) -> None:
        cfg, _ = cl.load(environ={"APP_DB__PASSWORD": "hunter2"})
        self.assertEqual(cl.masked(cfg)["db"]["password"], "***")
        self.assertEqual(cfg["db"]["password"], "hunter2")     # আসল মান বদলায় না


class CliTest(unittest.TestCase):
    def test_exit_codes(self) -> None:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cl.main(["--config", str(HERE / "app.toml")]), 0)
            self.assertEqual(cl.main(["--config", str(HERE / "app.json")]), 1)
            self.assertEqual(cl.main(["--config", str(HERE / "dup.json")]), 2)
            self.assertEqual(cl.main(["--set", "server.port=abc"]), 2)


if __name__ == "__main__":
    unittest.main()
