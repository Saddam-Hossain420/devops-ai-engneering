"""unittest wrapper — চালানো: python3 -m unittest -v

এই repo-র CI শুধু `unittest discover` চালায় এবং pytest install করে না। তাই:
  1. কয়েকটি মূল test এখানে unittest-এ (pytest ছাড়াও retention.py যাচাই হয়);
  2. pytest install থাকলে tests/ directory-র পুরো pytest suite subprocess-এ চালানো হয়, না থাকলে skip।
tests/-এ __init__.py নেই, তাই unittest discovery সেগুলো import করে না (pytest-এর fixture unittest বোঝে না)।
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import retention as r  # noqa: E402


class CoreTest(unittest.TestCase):
    def test_parse_name(self) -> None:
        self.assertEqual(r.parse_name("db-20261027T0300Z.sql.gz"), datetime(2026, 10, 27, 3, tzinfo=UTC))
        self.assertIsNone(r.parse_name("db-20261332T0300Z.sql.gz"))

    def test_newest_always_kept(self) -> None:
        paths = [Path("db-20261020T0300Z.gz"), Path("db-20261027T0300Z.gz")]
        result = r.plan(paths, datetime(2026, 10, 28, tzinfo=UTC), 0, 0, 0)
        self.assertEqual((result.keep, result.delete),
                         ({Path("db-20261027T0300Z.gz"): ["newest"]}, [Path("db-20261020T0300Z.gz")]))


class PytestSuite(unittest.TestCase):
    @unittest.skipIf(importlib.util.find_spec("pytest") is None, "pytest not installed")
    def test_pytest_suite_passes(self) -> None:
        proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                              cwd=HERE, capture_output=True, text=True, timeout=300)
        self.assertEqual(proc.returncode, 0, proc.stdout[-3000:] + proc.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
