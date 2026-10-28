#!/usr/bin/env python3
"""Semantic Versioning 2.0.0 — parse, precedence তুলনা, sort, এবং Conventional Commits থেকে পরের version।

  python3 semver.py compare 1.0.0-rc.1 1.0.0
  python3 semver.py sort 1.0.0 1.0.0-alpha 1.0.0-beta.11 1.0.0-beta.2
  python3 semver.py next --repo .            # সর্বশেষ vX.Y.Z tag-এর পরের commit message দেখে
  python3 semver.py next --current 1.4.2 --message "feat: add export" --message "fix: typo"

Exit: 0 OK, 2 invalid input।
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from functools import total_ordering
from pathlib import Path

# semver.org-এর প্রস্তাবিত regex (named group ছাড়া সমতুল্য)
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$")
CONVENTIONAL = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?(?P<bang>!)?: .+")


@total_ordering
@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    pre: tuple[str, ...] = ()
    build: str = field(default="", compare=False)

    @classmethod
    def parse(cls, text: str) -> "Version":
        m = SEMVER.match(text[1:] if text[:1] in "vV" else text)
        if not m:
            raise ValueError(f"not a semantic version: {text!r}")
        return cls(int(m[1]), int(m[2]), int(m[3]), tuple(m[4].split(".")) if m[4] else (), m[5] or "")

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        return s + (f"-{'.'.join(self.pre)}" if self.pre else "") + (f"+{self.build}" if self.build else "")

    def _key(self) -> tuple:
        # pre-release নেই > pre-release আছে; numeric identifier < alphanumeric; numeric সংখ্যা হিসেবে তুলনা
        pre = tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in self.pre)
        return (self.major, self.minor, self.patch, 0 if self.pre else 1, pre)

    def __lt__(self, other: "Version") -> bool:
        return self._key() < other._key()

    def __eq__(self, other: object) -> bool:   # build metadata precedence-এ গণ্য নয়
        return isinstance(other, Version) and self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def bump(self, kind: str) -> "Version":
        if kind == "major":
            return Version(self.major + 1, 0, 0)
        if kind == "minor":
            return Version(self.major, self.minor + 1, 0)
        if kind == "patch":
            # 1.2.3-rc.1 → patch release 1.2.3 (pre-release থেকে বের হওয়া)
            return Version(self.major, self.minor, self.patch if self.pre else self.patch + 1)
        raise ValueError(kind)


def classify(message: str) -> str | None:
    """Conventional Commits: BREAKING → major, feat → minor, fix/perf → patch, বাকি → None।"""
    first, _, body = message.partition("\n")
    m = CONVENTIONAL.match(first.strip())
    if re.search(r"^BREAKING[ -]CHANGE: ", body, re.MULTILINE) or (m and m["bang"]):
        return "major"
    if not m:
        return None
    return {"feat": "minor", "fix": "patch", "perf": "patch"}.get(m["type"])


def next_version(current: Version, messages: list[str]) -> tuple[Version | None, str | None]:
    order = {None: 0, "patch": 1, "minor": 2, "major": 3}
    kind = max((classify(m) for m in messages), key=lambda k: order[k], default=None)
    if kind is None:
        return None, None
    if kind == "major" and current.major == 0:
        kind = "minor"       # 0.y.z: public API অস্থির — breaking change-এ minor বাড়ানো প্রচলিত রীতি
    return current.bump(kind), kind


def latest_tag(repo: Path) -> tuple[Version, str]:
    tags = subprocess.run(["git", "-C", str(repo), "tag", "--list"], capture_output=True, text=True,
                          check=True).stdout.split()
    versions = []
    for t in tags:
        try:
            v = Version.parse(t)
        except ValueError:
            continue
        if not v.pre:          # release tag-ই ভিত্তি
            versions.append((v, t))
    if not versions:
        raise ValueError("no release tag (vX.Y.Z) found")
    return max(versions)


def messages_since(repo: Path, tag: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "log", f"{tag}..HEAD", "--format=%B%x00"],
                         capture_output=True, text=True, check=True).stdout
    return [m.strip() for m in out.split("\x00") if m.strip()]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Semantic versioning helper.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    s = sub.add_parser("sort")
    s.add_argument("versions", nargs="+")
    n = sub.add_parser("next")
    n.add_argument("--repo", type=Path)
    n.add_argument("--current")
    n.add_argument("--message", action="append", default=[])
    args = ap.parse_args(argv)
    try:
        if args.cmd == "compare":
            a, b = Version.parse(args.a), Version.parse(args.b)
            print(f"{a} {'<' if a < b else '>' if b < a else '=='} {b}")
        elif args.cmd == "sort":
            for v in sorted(Version.parse(x) for x in args.versions):
                print(v)
        else:
            if args.repo:
                current, tag = latest_tag(args.repo)
                msgs = messages_since(args.repo, tag)
                print(f"latest release tag: {tag}; {len(msgs)} commit(s) since")
            elif args.current:
                current, msgs = Version.parse(args.current), args.message
            else:
                raise ValueError("give --repo or --current")
            for m in msgs:
                print(f"  {classify(m) or '-':5}  {m.splitlines()[0]}")
            nxt, kind = next_version(current, msgs)
            print(f"next version: {nxt} ({kind})" if nxt else "no release needed (no feat/fix/breaking commits)")
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
