"""Tests for workflow_lint.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import workflow_lint as wl  # noqa: E402

REPO = HERE.parents[2]
HEADER = "name: t\non: [push]\npermissions:\n  contents: read\nconcurrency:\n  group: x\n"


def findings(body: str) -> list[str]:
    return wl.lint(HEADER + body)


class LintTest(unittest.TestCase):
    def test_bad_sample(self) -> None:
        out = wl.lint((HERE / "sample-bad-workflow.yml").read_text(encoding="utf-8"))
        kinds = [f.split()[0] for f in out]
        self.assertEqual(kinds.count("ERROR"), 3)       # write-all, pull_request_target checkout, injection
        self.assertEqual(kinds.count("WARN"), 4)        # দুটি unpinned, secret echo, timeout
        self.assertTrue(any("line 21" in f and "script injection" in f for f in out))

    def test_good_sample_is_clean(self) -> None:
        self.assertEqual(wl.lint((HERE / "sample-good-workflow.yml").read_text(encoding="utf-8")), [])

    def test_injection_inline_and_env_safe(self) -> None:
        bad = findings("jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n"
                       "      - run: echo ${{ github.head_ref }}\n")
        self.assertTrue(any("script injection" in f for f in bad))
        safe = findings("jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n"
                        "      - env:\n          REF: ${{ github.head_ref }}\n        run: echo \"$REF\"\n")
        self.assertEqual(safe, [])

    def test_trusted_contexts_not_flagged(self) -> None:
        out = findings("jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n"
                       "      - run: echo ${{ github.sha }} ${{ github.event.number }} ${{ matrix.os }}\n")
        self.assertEqual(out, [])

    def test_pinning(self) -> None:
        body = ("jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n"
                "      - uses: ./local-action\n"
                "      - uses: docker://alpine@sha256:" + "a" * 64 + "\n"
                "      - uses: actions/cache@" + "0" * 40 + " # v4\n"
                "      - uses: actions/cache@v4\n")
        out = findings(body)
        self.assertEqual(len(out), 1)
        self.assertIn("actions/cache@v4", out[0])

    def test_missing_permissions_and_timeouts(self) -> None:
        out = wl.lint("on: push\njobs:\n  one:\n    runs-on: x\n    steps:\n      - run: true\n"
                      "  two:\n    runs-on: x\n    timeout-minutes: 3\n    steps:\n      - run: true\n")
        text = "\n".join(out)
        self.assertIn("no top-level `permissions:`", text)
        self.assertIn("job `one` has no timeout-minutes", text)
        self.assertNotIn("job `two`", text)

    def test_repository_workflows_stay_clean(self) -> None:
        # এই repository-র নিজের workflow ও template — regression guard
        for path in [*(REPO / ".github" / "workflows").glob("*.yml"), REPO / "templates" / "github-actions-ci.yml"]:
            with self.subTest(path=path.name):
                self.assertEqual([f for f in wl.lint(path.read_text(encoding="utf-8")) if not f.startswith("INFO")], [])


if __name__ == "__main__":
    unittest.main()
