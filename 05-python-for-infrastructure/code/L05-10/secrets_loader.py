#!/usr/bin/env python3
"""secrets_loader.py — secret পড়া: env var > NAME_FILE (file-এর path) > .env file; মান কখনো print/log-এ নয়।

  from secrets_loader import get_secret
  db_password = get_secret("DB_PASSWORD", required=True)
  connect(password=db_password.reveal())          # শুধু ব্যবহারের মুহূর্তে আসল মান

  python3 secrets_loader.py DB_PASSWORD API_TOKEN --dotenv .env    # কোথা থেকে পাওয়া গেল (মান নয়) দেখায়

NAME_FILE রীতি: Docker/Kubernetes secret file হিসেবে mount হয় (/run/secrets/db_password) — env-এ মান থাকে না।
.env শুধু local development-এর জন্য; Git-এ কখনো নয়। কোনো ${VAR} expansion হয় না (ইচ্ছাকৃত)।
"""
from __future__ import annotations

import argparse
import os
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


class SecretStr:
    """repr/str/format-এ কখনো আসল মান দেখায় না — ভুল করে log বা traceback-এ গেলেও।"""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretStr('***')"

    def __str__(self) -> str:
        return "***"

    def __format__(self, spec: str) -> str:
        return "***"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SecretStr) and other._value == self._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __len__(self) -> int:
        return len(self._value)

    def __reduce__(self) -> tuple[object, ...]:
        raise TypeError("SecretStr cannot be pickled")      # ভুল করে cache/queue-তে না যায়


class SecretError(Exception):
    pass


@dataclass(frozen=True)
class Found:
    value: SecretStr
    source: str              # "env:NAME" / "file:/run/secrets/x" / "dotenv:.env"
    warnings: tuple[str, ...] = ()


def parse_dotenv(text: str) -> dict[str, str]:
    """সরল .env: KEY=VALUE, `export ` prefix, '#' comment, single/double quote। Expansion নেই।"""
    out: dict[str, str] = {}
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, sep, value = line.partition("=")
        key = key.strip()
        if not sep or not key.replace("_", "").isalnum():
            raise SecretError(f".env line {n}: expected KEY=VALUE")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()     # quote-হীন মানের পরে inline comment
        out[key] = value
    return out


def _file_warnings(path: Path) -> list[str]:
    if os.name != "posix":
        return []
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return [f"{path} is accessible by group/others (mode {stat.S_IMODE(mode):o}); use chmod 600"]
    return []


def get_secret(name: str, *, environ: Mapping[str, str] | None = None, dotenv: Path | None = None,
               required: bool = False) -> Found | None:
    env = os.environ if environ is None else environ
    if env.get(name):
        return Found(SecretStr(env[name]), f"env:{name}")
    file_var = f"{name}_FILE"
    if env.get(file_var):
        path = Path(env[file_var])
        try:
            value = path.read_text(encoding="utf-8").rstrip("\r\n")    # file-এর শেষের newline বাদ, মাঝেরটা নয়
        except OSError as exc:
            raise SecretError(f"{file_var}: cannot read {path}: {exc.strerror}") from None
        if not value:
            raise SecretError(f"{file_var}: {path} is empty")
        return Found(SecretStr(value), f"file:{path}", tuple(_file_warnings(path)))
    if dotenv is not None and dotenv.is_file():
        values = parse_dotenv(dotenv.read_text(encoding="utf-8"))
        if values.get(name):
            return Found(SecretStr(values[name]), f"dotenv:{dotenv}", tuple(_file_warnings(dotenv)))
    if required:
        raise SecretError(f"secret {name} not set (tried env {name}, env {file_var}"
                          + (f", {dotenv}" if dotenv else "") + ")")
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Show where secrets come from (never their values).")
    ap.add_argument("names", nargs="+")
    ap.add_argument("--dotenv", type=Path)
    args = ap.parse_args(argv)
    missing = 0
    for name in args.names:
        try:
            found = get_secret(name, dotenv=args.dotenv)
        except SecretError as exc:
            print(f"ERROR   {name}: {exc}", file=sys.stderr)
            missing += 1
            continue
        if found is None:
            print(f"MISSING {name}")
            missing += 1
            continue
        print(f"OK      {name:<14} from {found.source:<28} length={len(found.value)}")
        for w in found.warnings:
            print(f"WARN    {name}: {w}", file=sys.stderr)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
