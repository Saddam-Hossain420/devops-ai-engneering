#!/usr/bin/env python3
"""ছোট ADR (Architecture Decision Record) tool — docs-as-code অনুশীলনের জন্য।

ADR file: <dir>/NNNN-<slug>.md, প্রতিটিতে "- **Status:** <status>" লাইন ও
নির্দিষ্ট section থাকতে হবে।

Commands:
  python3 adr.py --dir docs/adr new "Use PostgreSQL for task storage"
  python3 adr.py --dir docs/adr list
  python3 adr.py --dir docs/adr supersede 2 "Move task storage to managed PostgreSQL"
  python3 adr.py --dir docs/adr lint        # CI-তে: সমস্যা থাকলে exit 1
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FILENAME_RE = re.compile(r"^(\d{4})-([a-z0-9-]+)\.md$")
STATUS_RE = re.compile(r"^- \*\*Status:\*\* (.+)$", re.MULTILINE)
TITLE_RE = re.compile(r"^# ADR-(\d{4}): (.+)$", re.MULTILINE)
REQUIRED_SECTIONS = ("## Context", "## Decision", "## Consequences")
VALID_STATUS = re.compile(r"^(Proposed|Accepted|Deprecated|Superseded by ADR-\d{4})$")

TEMPLATE = """# ADR-{number:04d}: {title}

- **Status:** Proposed
- **Date:** {today}

## Context

<!-- কোন সমস্যা বা প্রয়োজন থেকে সিদ্ধান্ত দরকার? constraint কী? -->

## Options considered

1. <!-- বিকল্প ১: সুবিধা / অসুবিধা -->
2. <!-- বিকল্প ২: সুবিধা / অসুবিধা -->

## Decision

<!-- কী বেছে নেওয়া হলো এবং মূল কারণ -->

## Consequences

<!-- ইতিবাচক, নেতিবাচক, ঝুঁকি; কখন পুনর্বিবেচনা -->
"""


@dataclass(frozen=True)
class Adr:
    number: int
    title: str
    status: str
    path: Path


def slugify(title: str) -> str:
    """'Use PostgreSQL for Tasks!' → 'use-postgresql-for-tasks'. ASCII-only filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError("title must contain at least one ASCII letter or digit")
    return slug[:60].rstrip("-")


def read_adrs(directory: Path) -> list[Adr]:
    adrs: list[Adr] = []
    if not directory.is_dir():
        return adrs
    for path in sorted(directory.iterdir()):
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        text = path.read_text(encoding="utf-8")
        title_m, status_m = TITLE_RE.search(text), STATUS_RE.search(text)
        adrs.append(Adr(int(m.group(1)),
                        title_m.group(2).strip() if title_m else "?",
                        status_m.group(1).strip() if status_m else "?",
                        path))
    return adrs


def next_number(directory: Path) -> int:
    return max((a.number for a in read_adrs(directory)), default=0) + 1


def create_adr(directory: Path, title: str, today: date | None = None) -> Path:
    title = title.strip()
    if not title:
        raise ValueError("title is empty")
    directory.mkdir(parents=True, exist_ok=True)
    number = next_number(directory)
    path = directory / f"{number:04d}-{slugify(title)}.md"
    # "x" mode: file আগে থেকে থাকলে overwrite না করে error — হারানো কাজ এড়াতে
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(TEMPLATE.format(number=number, title=title, today=(today or date.today()).isoformat()))
    return path


def supersede(directory: Path, old_number: int, new_title: str, today: date | None = None) -> Path:
    """নতুন ADR তৈরি এবং পুরোনোটির status 'Superseded by ADR-NNNN' করা। পুরোনো ADR মোছা হয় না।"""
    old = next((a for a in read_adrs(directory) if a.number == old_number), None)
    if old is None:
        raise ValueError(f"ADR-{old_number:04d} not found")
    new_path = create_adr(directory, new_title, today)
    new_number = int(new_path.name[:4])
    text = old.path.read_text(encoding="utf-8")
    old.path.write_text(STATUS_RE.sub(f"- **Status:** Superseded by ADR-{new_number:04d}", text, count=1),
                        encoding="utf-8", newline="\n")
    new_text = new_path.read_text(encoding="utf-8").replace(
        "## Context\n", f"## Context\n\nSupersedes ADR-{old_number:04d}.\n", 1)
    new_path.write_text(new_text, encoding="utf-8", newline="\n")
    return new_path


def lint(directory: Path) -> list[str]:
    problems: list[str] = []
    seen: set[int] = set()
    for adr in read_adrs(directory):
        name = adr.path.name
        text = adr.path.read_text(encoding="utf-8")
        if adr.number in seen:
            problems.append(f"{name}: duplicate number {adr.number:04d}")
        seen.add(adr.number)
        if adr.title == "?":
            problems.append(f"{name}: missing '# ADR-NNNN: title' heading")
        else:
            heading_number = int(TITLE_RE.search(text).group(1))
            if heading_number != adr.number:
                problems.append(f"{name}: heading says ADR-{heading_number:04d}")
        if not VALID_STATUS.match(adr.status):
            problems.append(f"{name}: invalid status {adr.status!r}")
        for section in REQUIRED_SECTIONS:
            if section not in text:
                problems.append(f"{name}: missing section '{section}'")
    for path in sorted(directory.glob("*.md")) if directory.is_dir() else []:
        if path.name != "README.md" and not FILENAME_RE.match(path.name):
            problems.append(f"{path.name}: filename must be NNNN-lowercase-slug.md")
    return problems


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Architecture Decision Record helper.")
    p.add_argument("--dir", type=Path, default=Path("docs/adr"), help="ADR directory")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("new").add_argument("title")
    sub.add_parser("list")
    s = sub.add_parser("supersede")
    s.add_argument("number", type=int)
    s.add_argument("title")
    sub.add_parser("lint")
    args = p.parse_args(argv)

    try:
        if args.cmd == "new":
            print(f"created {create_adr(args.dir, args.title)}")
        elif args.cmd == "supersede":
            print(f"created {supersede(args.dir, args.number, args.title)}")
        elif args.cmd == "list":
            for a in read_adrs(args.dir):
                print(f"ADR-{a.number:04d}  {a.status:26}  {a.title}")
        else:
            problems = lint(args.dir)
            for problem in problems:
                print(f"FAIL  {problem}")
            print(f"{len(read_adrs(args.dir))} ADR(s), {len(problems)} problem(s)")
            return 1 if problems else 0
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
