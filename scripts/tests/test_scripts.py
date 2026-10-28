"""Tests for scripts/progress.py and scripts/check_links.py (standard library unittest).

চালানো:  python3 -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_links  # noqa: E402
import progress  # noqa: E402


class CheckLinksTest(unittest.TestCase):
    def test_ignores_code_and_external(self) -> None:
        text = "[a](https://x.org)\n`[b](missing.md)`\n```\n[c](missing.md)\n```\n[d](real.md)\n"
        self.assertEqual(check_links.extract_links(text), [(1, "https://x.org"), (6, "real.md")])

    def test_detects_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.md").write_text("x", encoding="utf-8")
            (root / "index.md").write_text("[ok](ok.md) [bad](nope.md#x) [anchor](#top)", encoding="utf-8")
            problems = check_links.broken_links(root)
            self.assertEqual(problems, ["index.md:1: nope.md#x"])


class ProgressTest(unittest.TestCase):
    def _repo(self, tmp: Path) -> Path:
        mod = tmp / "00-orientation"
        mod.mkdir()
        (mod / "PROGRESS.md").write_text(
            "| ID | Lesson | Content | Learner | x |\n|---|---|---|---|---|\n"
            "| L00-01 | One | COMPLETED | Practiced | x |\n"
            "| L00-02 | Two | NOT_STARTED | Not started | x |\n",
            encoding="utf-8",
        )
        return tmp

    def test_next_skips_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lessons = progress.load_lessons(self._repo(Path(tmp)))
            self.assertEqual([lesson.id for lesson in progress.next_lessons(lessons, 5)], ["L00-02"])
            self.assertEqual(progress.validate(lessons), [])

    def test_real_repository_is_valid(self) -> None:
        lessons = progress.load_lessons()
        self.assertGreater(len(lessons), 300)
        self.assertEqual(progress.validate(lessons), [])


if __name__ == "__main__":
    unittest.main()
