"""Tests for secrets_loader.py ও scan_secrets.py — চালানো: python3 -m unittest -v

নকল secret-গুলো runtime-এ জোড়া দিয়ে বানানো হয় (যেমন "AKIA" + ...), যাতে এই file নিজে
scanner-এ (বা GitHub push protection-এ) ধরা না পড়ে। কোনোটিই আসল নয়।
"""
from __future__ import annotations

import io
import os
import pickle
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import scan_secrets as ss  # noqa: E402
import secrets_loader as sl  # noqa: E402

FAKE_AWS = "AKIA" + "Z" * 16
FAKE_GH = "ghp_" + "a1B2" * 9
FAKE_PW = "corr3ct-h0rse-" + "battery"


class SecretStrTest(unittest.TestCase):
    def test_never_shows_value(self) -> None:
        s = sl.SecretStr(FAKE_PW)
        for shown in (str(s), repr(s), f"{s}", f"{s!r}", "%s" % s, str([s]), str({"pw": s})):  # noqa: UP031
            with self.subTest(shown=shown):
                self.assertNotIn(FAKE_PW, shown)
        self.assertEqual(s.reveal(), FAKE_PW)

    def test_not_picklable(self) -> None:
        with self.assertRaises(TypeError):
            pickle.dumps(sl.SecretStr("x"))


class LoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_precedence_env_file_dotenv(self) -> None:
        f = self.dir / "db_password"
        f.write_text("from-file\n", encoding="utf-8")
        dotenv = self.dir / ".env"
        dotenv.write_text("DB_PASSWORD=from-dotenv\n", encoding="utf-8")
        env = {"DB_PASSWORD": "from-env", "DB_PASSWORD_FILE": str(f)}
        self.assertEqual(sl.get_secret("DB_PASSWORD", environ=env, dotenv=dotenv).source, "env:DB_PASSWORD")
        found = sl.get_secret("DB_PASSWORD", environ={"DB_PASSWORD_FILE": str(f)}, dotenv=dotenv)
        self.assertEqual(found.value.reveal(), "from-file")                  # শেষের newline বাদ
        found = sl.get_secret("DB_PASSWORD", environ={}, dotenv=dotenv)
        self.assertEqual((found.value.reveal(), found.source), ("from-dotenv", f"dotenv:{dotenv}"))

    def test_missing_and_required(self) -> None:
        self.assertIsNone(sl.get_secret("NOPE", environ={}))
        with self.assertRaisesRegex(sl.SecretError, "NOPE_FILE"):
            sl.get_secret("NOPE", environ={}, required=True)
        with self.assertRaisesRegex(sl.SecretError, "cannot read"):
            sl.get_secret("X", environ={"X_FILE": str(self.dir / "missing")})
        (self.dir / "empty").write_text("\n", encoding="utf-8")
        with self.assertRaisesRegex(sl.SecretError, "empty"):
            sl.get_secret("X", environ={"X_FILE": str(self.dir / "empty")})

    @unittest.skipUnless(os.name == "posix", "POSIX permissions")
    def test_world_readable_file_warns(self) -> None:
        f = self.dir / "token"
        f.write_text("t0ken-value", encoding="utf-8")
        f.chmod(0o644)
        self.assertTrue(sl.get_secret("T", environ={"T_FILE": str(f)}).warnings)
        f.chmod(stat.S_IRUSR | stat.S_IWUSR)
        self.assertFalse(sl.get_secret("T", environ={"T_FILE": str(f)}).warnings)

    def test_dotenv_parsing(self) -> None:
        text = ('# comment\nexport A=1\nB="two words"\nC=\'#notcomment\'\nD=plain # trailing\n'
                'E=has=equals\nF=${A}\n')
        self.assertEqual(sl.parse_dotenv(text),
                         {"A": "1", "B": "two words", "C": "#notcomment", "D": "plain", "E": "has=equals", "F": "${A}"})
        with self.assertRaises(sl.SecretError):
            sl.parse_dotenv("NOEQUALS\n")

    def test_cli_never_prints_value(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        dotenv = self.dir / ".env"
        dotenv.write_text(f"API_TOKEN={FAKE_PW}\n", encoding="utf-8")
        with redirect_stdout(out), redirect_stderr(err):
            code = sl.main(["API_TOKEN", "MISSING_ONE", "--dotenv", str(dotenv)])
        self.assertEqual(code, 1)
        self.assertNotIn(FAKE_PW, out.getvalue() + err.getvalue())
        self.assertIn(f"length={len(FAKE_PW)}", out.getvalue())


class ScannerTest(unittest.TestCase):
    def test_rules_detect(self) -> None:
        samples = {
            "aws-access-key-id": f"key_id = {FAKE_AWS}",
            "github-token": f"GH={FAKE_GH}",
            "private-key": "-----BEGIN OPENSSH " + "PRIVATE KEY-----",
            "url-password": "postgres://app:" + FAKE_PW + "@db/x",
            "assignment": 'db_password = "' + FAKE_PW + '"',
            "wireguard-private-key": "PrivateKey = " + "A" * 43 + "=",
        }
        for rule, line in samples.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, [f.rule for f in ss.scan_text(line, "x")])

    def test_letters_only_password_is_still_found(self) -> None:
        # regression: constant-নামের নিয়ম (?i)-এর ভেতরে থাকায় অক্ষর-সংখ্যার সব password বাদ পড়ছিল
        for value in ("correcthorse" + "battery", "Corr3ct" + "Horse9", "lowercase" + "only"):
            with self.subTest(value=value):
                self.assertEqual([f.rule for f in ss.scan_text(f'DB_PASSWORD = "{value}"', "x")], ["assignment"])
        self.assertEqual(list(ss.scan_text('nopasswd = "NOPASSWD"', "x")), [])

    def test_placeholders_and_inline_allow_are_ignored(self) -> None:
        for line in ('password = "changeme"', "https://user:TOKEN@host", 'api_key: "${API_KEY}"',
                     'token = "short"', f"key = {FAKE_AWS}  # scan-secrets: allow (doc example)"):
            with self.subTest(line=line):
                self.assertEqual(list(ss.scan_text(line, "x")), [])

    def test_masking(self) -> None:
        (f,) = ss.scan_text("postgres://app:" + FAKE_PW + "@db/x", "x")
        self.assertNotIn(FAKE_PW, f.preview)
        self.assertTrue(f.preview.startswith(FAKE_PW[:4]))

    def test_directory_scan_and_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "app.py").write_text(f'aws = "{FAKE_AWS}"\n', encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(f"{FAKE_AWS}\n", encoding="utf-8")   # .git বাদ
            (root / "blob.bin").write_bytes(b"\xff\xfe\x00" + FAKE_AWS.encode("utf-16-le"))
            findings, allowed, _ = ss.scan(root)
            self.assertEqual([(f.path, f.rule) for f in findings], [("app.py", "aws-access-key-id")])
            allow = root / "allow.txt"
            allow.write_text(f"{findings[0].fingerprint}  # test fixture\n", encoding="utf-8")
            findings, allowed, _ = ss.scan(root, allow)
            self.assertEqual((findings, allowed), ([], 1))

    def test_this_repository_is_clean(self) -> None:
        repo = HERE.parents[2]
        if not (repo / "PROGRESS.md").is_file():
            self.skipTest("not inside the course repository")
        findings, _, files = ss.scan(repo, HERE / "repo-allowlist.txt")
        self.assertGreater(files, 100)
        self.assertEqual([f"{f.path}:{f.line}:{f.rule}" for f in findings], [])


if __name__ == "__main__":
    unittest.main()
