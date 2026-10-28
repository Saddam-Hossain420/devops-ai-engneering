"""Tests for shlint_mini.py, run_checks.sh, and (if installed) the bats suite — চালানো: python3 -m unittest -v

ShellCheck ও bats না থাকলে সংশ্লিষ্ট test স্পষ্টভাবে skip হয় — কখনো চুপচাপ pass নয়।
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import shlint_mini as sl  # noqa: E402

BASH = shutil.which("bash")
CODE_DIR = HERE.parent


def rules(text: str) -> list[str]:
    return [r for _, r, _ in sl.lint_text(text)]


class ShlintMiniTest(unittest.TestCase):
    def test_sample_bad_all_rules(self) -> None:
        found = sl.lint_text((HERE / "sample-bad.sh").read_text(encoding="utf-8"))
        self.assertEqual([(n, r) for n, r, _ in found],
                         [(7, "M002"), (9, "M005"), (12, "M003"), (13, "M004"), (14, "M001"),
                          (17, "M006"), (21, "M001"), (21, "M005")])

    def test_quoted_and_guarded_forms_are_clean(self) -> None:
        good = ('set -euo pipefail\nrm -rf -- "${dir:?}/build"\ncp -- "$f" /tmp/\nwhile IFS= read -r line; do :; done\n'
                'local n; n=$(wc -l < f)\ncd -- "$d" || exit 1\n')
        self.assertEqual(rules(good), [])

    def test_false_positive_regressions(self) -> None:
        # প্রথম সংস্করণে এগুলো ভুলভাবে ধরা পড়ত (nested quote ও arithmetic) — এই module-এর নিজের script থেকে
        self.assertEqual(rules('tar -czf "$P" -C "$(dirname -- "$SOURCE")" "$NAME"\n'), [])
        self.assertEqual(rules("local extra=$(( ${#all[@]} - KEEP ))\n"), [])

    def test_heredoc_and_disable(self) -> None:
        self.assertEqual(rules("cat <<EOF\nrm -rf $X/y\nEOF\n"), [])
        self.assertEqual(rules("rm $f   # shlint-disable=M001\n"), [])

    def test_module_scripts_are_clean(self) -> None:
        # regression guard: L04-01-এর template-এর আসল SC2155 bug এই tool-ই ধরেছিল
        scripts = [p for p in CODE_DIR.rglob("*.sh") if "tests" not in p.parts and not p.name.startswith("sample-")]
        self.assertGreater(len(scripts), 8)
        for p in scripts:
            with self.subTest(script=p.relative_to(CODE_DIR).as_posix()):
                self.assertEqual(sl.lint_text(p.read_text(encoding="utf-8")), [])


@unittest.skipUnless(BASH, "bash not installed")
class RunChecksTest(unittest.TestCase):
    def run_checks(self, *args: str) -> subprocess.CompletedProcess:
        # ShellCheck/bats শুধু opt-in-এ (নিচের ShellCheckTest দেখুন) — নইলে যাচাই-না-করা finding-এ CI ভাঙত
        if os.environ.get("RUN_SHELLCHECK") != "1" and not args:
            args = ("--skip-external",)
        return subprocess.run([BASH, (HERE / "run_checks.sh").as_posix(), *args], capture_output=True,
                              text=True, encoding="utf-8", timeout=300)

    def test_reports_skips_explicitly(self) -> None:
        r = self.run_checks()
        self.assertIn("PASS shlint_mini", r.stdout)
        self.assertIn("PASS bash -n", r.stdout)
        for tool in ("shellcheck", "bats"):
            self.assertTrue(f"PASS {tool}" in r.stdout or f"SKIP {tool}" in r.stdout, tool)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_strict_and_usage(self) -> None:
        tools_present = shutil.which("shellcheck") and shutil.which("bats")
        if not tools_present:
            self.assertEqual(self.run_checks("--strict").returncode, 1)     # tool নেই → strict ব্যর্থ
        elif os.environ.get("RUN_SHELLCHECK") == "1":
            self.assertEqual(self.run_checks("--strict").returncode, 0)
        self.assertEqual(self.run_checks("--bogus").returncode, 2)


@unittest.skipUnless(shutil.which("bats") and os.environ.get("RUN_BATS") == "1",
                     "opt-in: install bats (Ubuntu: sudo apt install bats) and set RUN_BATS=1")
class BatsSuiteTest(unittest.TestCase):
    def test_bats_suite_passes(self) -> None:
        r = subprocess.run(["bats", str(HERE / "tests")], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


# Opt-in: এই repository-তে ShellCheck এখনো আসলে চালানো হয়নি, তাই যাচাই-না-করা প্রত্যাশা দিয়ে CI ভাঙা নয়।
# Ubuntu-তে: sudo apt install shellcheck && RUN_SHELLCHECK=1 python3 -m unittest -v — finding ঠিক করে
# তারপর CI-তে (validate.yml) RUN_SHELLCHECK=1 যোগ করুন।
@unittest.skipUnless(shutil.which("shellcheck") and os.environ.get("RUN_SHELLCHECK") == "1",
                     "opt-in: install shellcheck and set RUN_SHELLCHECK=1")
class ShellCheckTest(unittest.TestCase):
    def test_shellcheck_clean(self) -> None:
        scripts = [str(p) for p in CODE_DIR.rglob("*.sh") if "tests" not in p.parts and not p.name.startswith("sample-")]
        r = subprocess.run(["shellcheck", "-x", "--rcfile", str(HERE / "shellcheckrc"), *scripts],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_shellcheck_flags_sample(self) -> None:
        r = subprocess.run(["shellcheck", "-f", "gcc", str(HERE / "sample-bad.sh")], capture_output=True, text=True)
        for code in ("SC2155", "SC2045", "SC2086", "SC2162"):
            self.assertIn(code, r.stdout)


if __name__ == "__main__":
    unittest.main()
