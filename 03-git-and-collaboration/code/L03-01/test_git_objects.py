"""Tests for git_objects.py — চালানো: python3 -m unittest -v

Temporary directory-তে আসল `git` দিয়ে repository বানিয়ে আমাদের parser-এর ফল `git`-এর সাথে মেলানো।
User-এর global Git config ব্যবহার হয় না (আলাদা খালি config, নির্দিষ্ট author/তারিখ → hash পুনরুৎপাদনযোগ্য)।
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

import git_objects as go  # noqa: E402

GIT = shutil.which("git")


def git_env(tmp: Path) -> dict[str, str]:
    empty = tmp / "empty-gitconfig"
    empty.write_text("")
    env = dict(os.environ, GIT_CONFIG_GLOBAL=str(empty), GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Lab User", GIT_AUTHOR_EMAIL="lab@example.com",
               GIT_COMMITTER_NAME="Lab User", GIT_COMMITTER_EMAIL="lab@example.com",
               GIT_AUTHOR_DATE="2026-01-01T00:00:00+0000", GIT_COMMITTER_DATE="2026-01-01T00:00:00+0000")
    return env


class HashTest(unittest.TestCase):
    def test_known_hashes(self) -> None:
        self.assertEqual(go.hash_object(b""), "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391")        # খালি blob
        self.assertEqual(go.hash_object(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_parse_tree_binary(self) -> None:
        raw = bytes.fromhex("ce013625030ba8dba906f756967f9e9ca394464a")
        body = b"100644 a.txt\x00" + raw + b"40000 dir\x00" + raw
        self.assertEqual(go.parse_tree(body), [("100644", "a.txt", raw.hex()), ("040000", "dir", raw.hex())])


@unittest.skipUnless(GIT, "git not installed")
class RepoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="gitobj-"))
        self.repo = self.tmp / "repo"
        self.env = git_env(self.tmp)
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.tmp)
        (self.repo / "app.py").write_text("print('v1')\n")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "README.md").write_text("# docs\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "first")
        (self.repo / "app.py").write_text("print('v2')\n")
        self.git("commit", "-q", "-am", "second")
        self.git("tag", "-a", "v1.0.0", "-m", "release")
        self.gd = self.repo / ".git"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, *args: str, cwd: Path | None = None) -> str:
        r = subprocess.run([GIT, *args], cwd=cwd or self.repo, env=self.env, capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def test_hash_matches_git(self) -> None:
        self.assertEqual(go.hash_object((self.repo / "app.py").read_bytes()), self.git("hash-object", "app.py"))

    def test_resolve_head_branch_tag(self) -> None:
        head = self.git("rev-parse", "HEAD")
        self.assertEqual(go.resolve(self.gd, "HEAD"), head)
        self.assertEqual(go.resolve(self.gd, "main"), head)
        self.assertEqual(go.resolve(self.gd, "v1.0.0"), head)      # annotated tag → commit-এ peel

    def test_commit_and_tree_match_git(self) -> None:
        head = self.git("rev-parse", "HEAD")
        c = go.parse_commit(go.read_object(self.gd, head)[1])
        self.assertEqual(c["tree"], self.git("rev-parse", "HEAD^{tree}"))
        self.assertEqual(c["parents"], [self.git("rev-parse", "HEAD~1")])
        self.assertTrue(c["author"].startswith("Lab User <lab@example.com> 1767225600"))
        ours = [f"{m} {'tree' if m == '040000' else 'blob'} {s}\t{n}" for m, n, s in go.parse_tree(go.read_object(self.gd, c["tree"])[1])]
        self.assertEqual(ours, self.git("ls-tree", "HEAD").splitlines())

    def test_unchanged_file_shares_blob(self) -> None:
        # docs/README.md দুই commit-এ বদলায়নি → একই blob, নতুন copy নয়
        self.assertEqual(self.git("rev-parse", "HEAD:docs/README.md"), self.git("rev-parse", "HEAD~1:docs/README.md"))
        self.assertNotEqual(self.git("rev-parse", "HEAD:app.py"), self.git("rev-parse", "HEAD~1:app.py"))

    def test_write_object_readable_by_git(self) -> None:
        sha = go.write_object(self.gd, b"written by python\n")
        self.assertEqual(self.git("cat-file", "-t", sha), "blob")
        self.assertEqual(self.git("cat-file", "-p", sha), "written by python")

    def test_corruption_detected(self) -> None:
        sha = self.git("rev-parse", "HEAD:app.py")
        p = go.object_path(self.gd, sha)
        p.chmod(0o644)
        p.write_bytes(__import__("zlib").compress(b"blob 12\x00print('v3')\n"))
        with self.assertRaises(ValueError):
            go.read_object(self.gd, sha)


if __name__ == "__main__":
    unittest.main()
