"""Tests for codeowners.py and protection_check.py — চালানো: python3 -m unittest -v

CODEOWNERS-এর প্রত্যাশিত ফল GitHub documentation-এর উদাহরণ থেকে নেওয়া।
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import codeowners as co  # noqa: E402
import protection_check as pc  # noqa: E402

GITHUB_DOC_EXAMPLE = """
*       @global-owner1 @global-owner2
*.js    @js-owner #This is an inline comment.
*.go docs@example.com
*.txt @octo-org/octocats
/build/logs/ @doctocat
docs/*  docs@example.com
apps/ @octocat
/docs/ @doctocat
/scripts/ @doctocat @octocat
**/logs @octocat
/apps/ @octocat
/apps/github
"""


class CodeownersTest(unittest.TestCase):
    def setUp(self) -> None:
        self.rules, self.problems = co.parse(GITHUB_DOC_EXAMPLE)

    def owners(self, path: str) -> list[str]:
        return co.owners_for(self.rules, path)[0]

    def test_last_match_wins(self) -> None:
        self.assertEqual(self.owners("README.md"), ["@global-owner1", "@global-owner2"])
        self.assertEqual(self.owners("src/app.js"), ["@js-owner"])          # inline comment বাদ
        self.assertEqual(self.owners("build/logs/out.txt"), ["@octocat"])   # **/logs সবার শেষে

    def test_directory_patterns(self) -> None:
        self.assertEqual(self.owners("deep/apps/x.rb"), ["@octocat"])        # apps/ যেকোনো গভীরতায়
        self.assertEqual(self.owners("scripts/deploy/run.sh"), ["@doctocat", "@octocat"])
        self.assertEqual(self.owners("deeply/nested/logs/a.log"), ["@octocat"])

    def test_empty_owners_removes_ownership(self) -> None:
        self.assertEqual(self.owners("apps/github/main.rb"), [])
        self.assertEqual(self.owners("apps/other/main.rb"), ["@octocat"])

    def test_docs_star_only_direct_children(self) -> None:
        rules, _ = co.parse("docs/* docs@example.com\n")
        self.assertEqual(co.owners_for(rules, "docs/getting-started.md")[0], ["docs@example.com"])
        self.assertEqual(co.owners_for(rules, "docs/build-app/troubleshooting.md")[0], [])

    def test_sample_lint(self) -> None:
        rules, problems = co.parse((HERE / "sample-CODEOWNERS").read_text(encoding="utf-8"))
        findings = co.lint(rules, problems, [".github/workflows/", "infra/terraform/"])
        text = "\n".join(findings)
        self.assertIn("invalid owner 'platform-team'", text)
        self.assertIn("negation is not supported", text)
        self.assertIn("pattern '*.md' repeats", text)
        self.assertIn("required path infra/terraform/ has no owner", text)
        self.assertNotIn(".github/workflows/ has no owner", text)
        self.assertEqual(len(findings), 4)

    def test_sample_payments_needs_security(self) -> None:
        rules, _ = co.parse((HERE / "sample-CODEOWNERS").read_text(encoding="utf-8"))
        self.assertEqual(co.owners_for(rules, "app/payments/charge.py")[0], ["@acme/payments", "@acme/security"])
        self.assertEqual(co.owners_for(rules, "app/payments/migrations/0001.sql")[0], ["@acme/dba"])


@unittest.skipUnless(shutil.which("git"), "git not installed")
class ReviewFromGitTest(unittest.TestCase):
    def test_changed_files(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="owners-"))
        try:
            cfg = tmp / "c"
            cfg.write_text("")
            env = dict(os.environ, GIT_CONFIG_GLOBAL=str(cfg), GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="T",
                       GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="T", GIT_COMMITTER_EMAIL="t@example.com")
            repo = tmp / "r"

            def git(*a: str) -> None:
                subprocess.run(["git", *a], cwd=repo, env=env, check=True, capture_output=True)

            subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], env=env, check=True)
            (repo / "README.md").write_text("x")
            git("add", ".")
            git("commit", "-q", "-m", "init")
            git("switch", "-q", "-c", "feature")
            (repo / "app").mkdir()
            (repo / "app" / "api.py").write_text("x")
            git("add", ".")
            git("commit", "-q", "-m", "feat: api")
            self.assertEqual(co.changed_files(repo, "main"), ["app/api.py"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ProtectionTest(unittest.TestCase):
    def test_sample(self) -> None:
        data = json.loads((HERE / "sample-protection.json").read_text(encoding="utf-8"))
        failed = [t for ok, t in pc.check(data, 1, ["validate"]) if not ok]
        self.assertEqual(failed, ["new commits dismiss stale approvals",
                                  "branch must be up to date with base before merging",
                                  "rules apply to administrators too"])

    def test_unprotected(self) -> None:
        results = pc.check({}, 1, [])
        self.assertFalse(results[0][0])                     # PR বাধ্যতামূলক নয়
        self.assertTrue(dict((t, ok) for ok, t in results)["force push disabled"])   # অনুপস্থিত = বন্ধ


if __name__ == "__main__":
    unittest.main()
