"""Tests for getopts_demo.sh and backup.sh — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASH = shutil.which("bash")


def run(script: str, *args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess:
    e = {k: v for k, v in os.environ.items() if not k.startswith("BACKUP_")}
    e.update(env or {})
    return subprocess.run([BASH, (HERE / script).as_posix(), *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=60, env=e, cwd=cwd)


@unittest.skipUnless(BASH, "bash not installed")
class GetoptsTest(unittest.TestCase):
    def test_combined_flags_and_double_dash(self) -> None:
        r = run("getopts_demo.sh", "-vvn", "-oout.txt", "--", "-file")
        self.assertEqual(r.stdout.strip(), "verbose=2 dry_run=1 output=[out.txt] remaining(1): [-file]")

    def test_stops_at_first_non_option(self) -> None:
        r = run("getopts_demo.sh", "a", "-v")
        self.assertIn("verbose=0", r.stdout)
        self.assertIn("remaining(2): [a] [-v]", r.stdout)

    def test_errors(self) -> None:
        self.assertIn("-o needs a value", run("getopts_demo.sh", "-o").stderr)
        r = run("getopts_demo.sh", "-z")
        self.assertEqual((r.returncode, "unknown option -z" in r.stderr), (2, True))


@unittest.skipUnless(BASH and shutil.which("tar") and shutil.which("realpath"), "bash/tar/realpath not installed")
class BackupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="backup-"))
        self.src = self.tmp / "my app"
        (self.src / "logs").mkdir(parents=True)
        (self.src / "config.ini").write_text("x")
        (self.src / "logs" / "a.log").write_text("y")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def config(self, *args: str, env: dict[str, str] | None = None) -> dict[str, list[str]]:
        r = run("backup.sh", *args, "--print-config", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        out: dict[str, list[str]] = {}
        for line in r.stdout.splitlines():
            k, _, v = line.partition("=")
            out.setdefault(k, []).append(v)
        return out

    def test_precedence_cli_over_env(self) -> None:
        env = {"BACKUP_SOURCE": self.src.as_posix(), "BACKUP_DEST": (self.tmp / "env").as_posix()}
        self.assertTrue(self.config(env=env)["dest"][0].endswith("/env"))
        cli = self.config("--dest=" + (self.tmp / "cli").as_posix(), env=env)
        self.assertTrue(cli["dest"][0].endswith("/cli"))

    def test_long_and_short_forms_and_repeatable(self) -> None:
        c = self.config("-s", self.src.as_posix(), "--dest", (self.tmp / "d").as_posix(),
                        "-x", "*.log", "--exclude=tmp", "-q")
        self.assertEqual(c["exclude"], ["*.log", "tmp"])
        self.assertEqual(c["log_level"], ["2"])

    def test_real_backup_excludes_and_logs_to_file_even_quiet(self) -> None:
        log = (self.tmp / "b.log").as_posix()
        r = run("backup.sh", "-q", "--log-file", log, "-s", self.src.as_posix(),
                "-d", (self.tmp / "backups").as_posix(), "-x", "*.log")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr, "")                                  # quiet console
        archive = r.stdout.strip()
        names = tarfile.open(subprocess.run([BASH, "-c", f'cygpath -w "{archive}" 2>/dev/null || echo "{archive}"'],
                                            capture_output=True, text=True).stdout.strip()).getnames()
        self.assertIn("my app/config.ini", names)
        self.assertNotIn("my app/logs/a.log", names)
        self.assertIn("INFO", Path(log).read_text())                    # file-এ তবু info

    def test_dry_run_writes_nothing(self) -> None:
        r = run("backup.sh", "-n", "-s", self.src.as_posix(), "-d", (self.tmp / "backups").as_posix())
        self.assertEqual(r.returncode, 0)
        self.assertFalse((self.tmp / "backups").exists())

    def test_usage_errors(self) -> None:
        s = self.src.as_posix()
        for args in (["-s"], ["--frobnicate"], ["-s", s], ["extra"], ["-s", s, "-d", "--dry-run"]):
            with self.subTest(args=args):
                self.assertEqual(run("backup.sh", *args).returncode, 2)

    def test_dest_inside_source_rejected_even_relative(self) -> None:
        self.assertEqual(run("backup.sh", "-n", "-s", ".", "-d", "./backups", cwd=self.src).returncode, 2)
        self.assertEqual(run("backup.sh", "-n", "-s", "my app", "-d", "my app/../my app/x", cwd=self.tmp).returncode, 2)
        self.assertEqual(run("backup.sh", "-n", "-s", "my app", "-d", "backups", cwd=self.tmp).returncode, 0)


if __name__ == "__main__":
    unittest.main()
