"""Tests for adr.py — চালানো: python3 -m unittest -v (এই folder থেকে)।"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import adr  # noqa: E402

DAY = date(2026, 10, 26)


class SlugTest(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(adr.slugify("Use PostgreSQL for Tasks!"), "use-postgresql-for-tasks")
        self.assertEqual(adr.slugify("  K8s / Helm  "), "k8s-helm")

    def test_non_ascii_only_rejected(self) -> None:
        with self.assertRaises(ValueError):
            adr.slugify("ডাটাবেস")


class TempDirTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.dir)


class CreateTest(TempDirTest):
    def test_numbering_and_content(self) -> None:
        first = adr.create_adr(self.dir, "Use PostgreSQL", DAY)
        second = adr.create_adr(self.dir, "Use Redis cache", DAY)
        self.assertEqual(first.name, "0001-use-postgresql.md")
        self.assertEqual(second.name, "0002-use-redis-cache.md")
        text = second.read_text(encoding="utf-8")
        self.assertIn("# ADR-0002: Use Redis cache", text)
        self.assertIn("- **Date:** 2026-10-26", text)
        self.assertEqual(adr.lint(self.dir), [])

    def test_existing_file_not_overwritten(self) -> None:
        (self.dir / "0001-same.md").write_text("keep me", encoding="utf-8")
        # next number is 2, so create a clash deliberately on 0002
        (self.dir / "0002-same.md").write_text("# ADR-0002: x\n- **Status:** Accepted\n", encoding="utf-8")
        path = adr.create_adr(self.dir, "same", DAY)
        self.assertEqual(path.name, "0003-same.md")
        self.assertEqual((self.dir / "0001-same.md").read_text(encoding="utf-8"), "keep me")


class SupersedeTest(TempDirTest):
    def test_supersede_updates_old_status(self) -> None:
        adr.create_adr(self.dir, "Use SQLite", DAY)
        new = adr.supersede(self.dir, 1, "Use PostgreSQL", DAY)
        records = {a.number: a for a in adr.read_adrs(self.dir)}
        self.assertEqual(records[1].status, "Superseded by ADR-0002")
        self.assertIn("Supersedes ADR-0001.", new.read_text(encoding="utf-8"))
        self.assertEqual(adr.lint(self.dir), [])

    def test_supersede_missing(self) -> None:
        with self.assertRaises(ValueError):
            adr.supersede(self.dir, 9, "x", DAY)


class LintTest(TempDirTest):
    def test_detects_problems(self) -> None:
        (self.dir / "0001-bad.md").write_text(
            "# ADR-0003: Wrong number\n\n- **Status:** Maybe\n\n## Context\n", encoding="utf-8")
        (self.dir / "notes.md").write_text("x", encoding="utf-8")
        problems = adr.lint(self.dir)
        self.assertIn("0001-bad.md: heading says ADR-0003", problems)
        self.assertIn("0001-bad.md: invalid status 'Maybe'", problems)
        self.assertIn("0001-bad.md: missing section '## Decision'", problems)
        self.assertIn("notes.md: filename must be NNNN-lowercase-slug.md", problems)

    def test_example_adrs_are_clean(self) -> None:
        self.assertEqual(adr.lint(HERE / "example-adr"), [])
        self.assertEqual(len(adr.read_adrs(HERE / "example-adr")), 2)

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(adr.main(["--dir", str(HERE / "example-adr"), "lint"]), 0)
        (self.dir / "0001-x.md").write_text("no heading", encoding="utf-8")
        self.assertEqual(adr.main(["--dir", str(self.dir), "lint"]), 1)
        self.assertEqual(adr.main(["--dir", str(self.dir), "new", "!!!"]), 2)


if __name__ == "__main__":
    unittest.main()
