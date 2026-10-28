"""Tests for envconfig.py — চালানো: python3 -m unittest -v (এই folder থেকে)।"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import envconfig as ec  # noqa: E402

SECRET_ENV = {"APP_DATABASE__PASSWORD": "s3cr3t"}


class MergeTest(unittest.TestCase):
    def test_deep_merge_does_not_mutate(self) -> None:
        base = {"a": {"x": 1, "y": 2}, "b": 1}
        out = ec.deep_merge(base, {"a": {"y": 9}})
        self.assertEqual(out, {"a": {"x": 1, "y": 9}, "b": 1})
        self.assertEqual(base["a"]["y"], 2)

    def test_env_overrides_types_and_nesting(self) -> None:
        env = {"APP_DATABASE__POOL_SIZE": "20", "APP_APP__DEBUG": "false",
               "APP_APP__NAME": "x-api", "PATH": "/usr/bin"}
        self.assertEqual(ec.env_overrides(env),
                         {"database": {"pool_size": 20}, "app": {"debug": False, "name": "x-api"}})


class LoadTest(unittest.TestCase):
    def test_precedence(self) -> None:
        cfg = ec.load_config("prod", {"APP_DATABASE__POOL_SIZE": "50", **SECRET_ENV})
        self.assertEqual(cfg["app"]["port"], 8000)               # base
        self.assertEqual(cfg["database"]["host"], "db.prod.internal")  # prod.json
        self.assertEqual(cfg["database"]["pool_size"], 50)        # env var wins
        self.assertEqual(cfg["environment"], "prod")

    def test_unknown_env(self) -> None:
        with self.assertRaises(ValueError):
            ec.load_config("qa", {})

    def test_secret_in_file_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "base.json").write_text(json.dumps({"database": {"password": "oops"}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                ec.load_config("dev", {}, config_dir=d)


class ValidateTest(unittest.TestCase):
    def test_prod_ok_with_secret(self) -> None:
        self.assertEqual(ec.validate(ec.load_config("prod", SECRET_ENV)), [])

    def test_prod_missing_password(self) -> None:
        errors = ec.validate(ec.load_config("prod", {}))
        self.assertTrue(any("password" in e for e in errors))

    def test_prod_debug_rejected(self) -> None:
        errors = ec.validate(ec.load_config("prod", {**SECRET_ENV, "APP_APP__DEBUG": "true"}))
        self.assertIn("app.debug must be false in prod", errors)

    def test_dev_allows_debug_and_localhost(self) -> None:
        self.assertEqual(ec.validate(ec.load_config("dev", {})), [])


class DiffAndMaskTest(unittest.TestCase):
    def test_secret_masked(self) -> None:
        out = ec.masked(ec.load_config("prod", SECRET_ENV))
        self.assertEqual(out["database"]["password"], "***")
        self.assertNotIn("s3cr3t", json.dumps(out))

    def test_staging_prod_diff(self) -> None:
        rows = ec.diff(ec.load_config("staging", SECRET_ENV), ec.load_config("prod", SECRET_ENV))
        self.assertEqual([r[0] for r in rows],
                         ["database.host", "database.pool_size", "environment", "features.new_dashboard"])


if __name__ == "__main__":
    unittest.main()
