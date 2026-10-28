"""Tests for graph.py and conflict_markers.py — চালানো: python3 -m unittest -v

Graph-এর ফল আসল `git merge-base`/`rev-list`-এর সাথে মেলানো হয় (temporary repository, global config ছাড়া)।
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import conflict_markers as cm  # noqa: E402
import graph as gr  # noqa: E402

GIT = shutil.which("git")


class ConflictMarkerTest(unittest.TestCase):
    def test_detects_markers(self) -> None:
        text = "a\n<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> feature\nb\n"
        self.assertEqual([n for n, _ in cm.scan(text)], [2, 4, 6])

    def test_diff3_style(self) -> None:
        text = "<<<<<<< HEAD\nours\n||||||| base\nold\n=======\ntheirs\n>>>>>>> f\n"
        self.assertEqual(len(cm.scan(text)), 4)

    def test_markdown_underline_is_not_a_marker(self) -> None:
        self.assertEqual(cm.scan("Title\n=======\ntext\n"), [])         # "<<<<<<<" ছাড়া
        self.assertEqual(cm.scan("<<<<<<<<< not eight\n"), [])          # ঠিক ৭টি নয়


@unittest.skipUnless(GIT, "git not installed")
class GraphTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="graph-"))
        cfg = self.tmp / "empty.cfg"
        cfg.write_text("")
        self.env = dict(os.environ, GIT_CONFIG_GLOBAL=str(cfg), GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="T", GIT_AUTHOR_EMAIL="t@example.com",
                        GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.com")
        self.repo = self.tmp / "r"
        self.n = 0
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.tmp)
        self.commit("A")
        self.commit("B")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run([GIT, *args], cwd=cwd or self.repo, env=self.env,
                              capture_output=True, text=True, check=True).stdout.strip()

    def commit(self, name: str) -> None:
        self.n += 1
        (self.repo / f"{name}.txt").write_text(name)
        self.git("add", ".")
        self.git("commit", "-q", "-m", name)

    def check_against_git(self, a: str, b: str) -> None:
        g = gr.load_graph(self.repo)
        ra, rb = gr.rev_parse(self.repo, a), gr.rev_parse(self.repo, b)
        self.assertEqual(gr.merge_bases(g, ra, rb), set(self.git("merge-base", "--all", a, b).split()))
        left, right = map(int, self.git("rev-list", "--left-right", "--count", f"{a}...{b}").split())
        self.assertEqual(gr.ahead_behind(g, ra, rb), (left, right))

    def test_fast_forward(self) -> None:
        self.git("switch", "-q", "-c", "feature")
        self.commit("F1")
        g = gr.load_graph(self.repo)
        self.assertIn("fast-forward", gr.advice(g, gr.rev_parse(self.repo, "main"), gr.rev_parse(self.repo, "feature")))
        self.check_against_git("feature", "main")

    def test_diverged(self) -> None:
        self.git("switch", "-q", "-c", "feature")
        self.commit("F1")
        self.commit("F2")
        self.git("switch", "-q", "main")
        self.commit("C")
        g = gr.load_graph(self.repo)
        self.assertIn("diverged", gr.advice(g, gr.rev_parse(self.repo, "main"), gr.rev_parse(self.repo, "feature")))
        self.check_against_git("feature", "main")

    def test_criss_cross_has_two_merge_bases(self) -> None:
        self.git("switch", "-q", "-c", "x")
        self.commit("X1")
        self.git("switch", "-q", "main")
        self.commit("M1")
        self.git("branch", "x-before", "x")
        self.git("merge", "-q", "--no-edit", "x")                   # main ← x
        self.git("switch", "-q", "x")
        self.git("merge", "-q", "--no-edit", "main~1")              # x ← main-এর পুরোনো tip (criss-cross)
        self.git("switch", "-q", "main")
        self.commit("M2")
        self.git("switch", "-q", "x")
        self.commit("X2")
        g = gr.load_graph(self.repo)
        bases = gr.merge_bases(g, gr.rev_parse(self.repo, "main"), gr.rev_parse(self.repo, "x"))
        self.assertEqual(len(bases), 2)
        self.check_against_git("main", "x")

    def test_cli(self) -> None:
        self.assertEqual(gr.main(["main", "main", "--repo", str(self.repo)]), 0)
        self.assertEqual(gr.main(["main", "no-such-branch", "--repo", str(self.repo)]), 2)


if __name__ == "__main__":
    unittest.main()
