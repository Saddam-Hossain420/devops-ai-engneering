#!/usr/bin/env python3
"""CODEOWNERS — কোন file-এর owner কে, একটি PR-এ কাদের review লাগবে, এবং file-এর lint।
GitHub-এর নিয়ম: gitignore-ধাঁচের pattern, **শেষ মিলে যাওয়া লাইন জেতে**, owner ছাড়া লাইন = owner নেই।

  python3 codeowners.py owners sample-CODEOWNERS src/app.js apps/github/x.rb
  python3 codeowners.py review sample-CODEOWNERS --repo . --base origin/main     # PR-এর পরিবর্তিত file থেকে
  python3 codeowners.py lint sample-CODEOWNERS --require .github/workflows/ --require infra/

GitHub-এর CODEOWNERS-এ যা নেই: `!` negation, `[ ]` character range — lint এগুলো ধরে।
Exit: owners/review → 0; lint → 0 পরিষ্কার / 1 finding; 2 input error।
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

OWNER = re.compile(r"^(@[A-Za-z0-9-]+(/[A-Za-z0-9._-]+)?|[^@\s]+@[^@\s]+\.[^@\s]+)$")   # @user, @org/team, email


@dataclass
class Rule:
    line: int
    pattern: str
    owners: list[str]
    regex: re.Pattern


def to_regex(pattern: str) -> re.Pattern:
    dir_only = pattern.endswith("/")
    p = pattern.rstrip("/")
    anchored = p.startswith("/") or "/" in p          # মাঝে '/' থাকলে root-এর সাপেক্ষে (gitignore নিয়ম)
    p = p.lstrip("/")
    out, i = [], 0
    while i < len(p):
        if p.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif p.startswith("**", i):
            out.append(".*")
            i += 2
        elif p[i] == "*":
            out.append("[^/]*")
            i += 1
        elif p[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(p[i]))
            i += 1
    body = "".join(out)
    prefix = "^" if anchored else "^(?:.*/)?"
    if dir_only:
        return re.compile(prefix + body + "/.*$")
    if pattern.endswith("/*"):
        # GitHub-এর ব্যতিক্রম: "docs/*" শুধু docs-এর সরাসরি file, docs/sub/x নয়
        return re.compile(prefix + body + "$")
    return re.compile(prefix + body + "(?:/.*)?$")     # file নিজে, বা directory হলে তার সব কিছু


def parse(text: str) -> tuple[list[Rule], list[str]]:
    rules, problems = [], []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"\s+#.*$", "", line)               # লাইনের শেষের comment
        pattern, *owners = line.split()
        if pattern.startswith("!"):
            problems.append(f"line {n}: '!' negation is not supported in CODEOWNERS — pattern ignored")
            continue
        if "[" in pattern:
            problems.append(f"line {n}: '[ ]' ranges are not supported in CODEOWNERS — pattern ignored")
            continue
        for o in owners:
            if not OWNER.match(o):
                problems.append(f"line {n}: invalid owner {o!r} (use @user, @org/team or an email)")
        rules.append(Rule(n, pattern, owners, to_regex(pattern)))
    return rules, problems


def owners_for(rules: list[Rule], path: str) -> tuple[list[str], Rule | None]:
    match = None
    for r in rules:                                         # শেষ মিলটিই জেতে
        if r.regex.match(path):
            match = r
    return (match.owners if match else []), match


def lint(rules: list[Rule], problems: list[str], required: list[str]) -> list[str]:
    out = list(problems)
    seen: dict[str, int] = {}
    for r in rules:
        if r.pattern in seen:
            out.append(f"line {r.line}: pattern {r.pattern!r} repeats line {seen[r.pattern]} — the earlier one never applies")
        seen[r.pattern] = r.line
    if not any(r.pattern == "*" for r in rules):
        out.append("no catch-all '*' rule: files outside listed paths have no owner")
    for req in required:
        probe = req.rstrip("/") + "/example" if req.endswith("/") else req
        owners, rule = owners_for(rules, probe.lstrip("/"))
        if not owners:
            how = f"line {rule.line} {rule.pattern!r} removes owners" if rule else "no rule matches"
            out.append(f"required path {req} has no owner ({how})")
    return out


def changed_files(repo: Path, base: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", f"{base}...HEAD"],
                         capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Work with a GitHub CODEOWNERS file.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("owners")
    o.add_argument("file", type=Path)
    o.add_argument("paths", nargs="+")
    r = sub.add_parser("review")
    r.add_argument("file", type=Path)
    r.add_argument("--repo", type=Path, default=Path("."))
    r.add_argument("--base", default="origin/main")
    l = sub.add_parser("lint")
    l.add_argument("file", type=Path)
    l.add_argument("--require", action="append", default=[])
    args = ap.parse_args(argv)
    try:
        rules, problems = parse(args.file.read_text(encoding="utf-8"))
        paths = changed_files(args.repo, args.base) if args.cmd == "review" else getattr(args, "paths", [])
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {getattr(exc, 'stderr', '') or exc}".strip(), file=sys.stderr)
        return 2
    if args.cmd == "lint":
        findings = lint(rules, problems, args.require)
        for f in findings:
            print(f"- {f}")
        print(f"{len(rules)} rule(s), {len(findings)} finding(s)")
        return 1 if findings else 0
    needed: dict[str, list[str]] = {}
    for p in paths:
        owners, rule = owners_for(rules, p)
        where = f"(line {rule.line}: {rule.pattern})" if rule else "(no rule)"
        print(f"{p:40} {' '.join(owners) or '— no owner'}  {where}")
        for ow in owners:
            needed.setdefault(ow, []).append(p)
    if args.cmd == "review":
        print(f"\n{len(paths)} changed file(s); review requested from: {', '.join(needed) or 'nobody'}")
        print("(GitHub requires ONE approval from any listed owner of each file when code-owner review is enforced)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
