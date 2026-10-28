#!/usr/bin/env python3
"""Repository progress tool.

Module folder-এর PROGRESS.md table পড়ে মোট অগ্রগতি ও পরের lesson দেখায়।
Source of truth: <module>/PROGRESS.md (Markdown table) — এই script শুধু পড়ে, কিছু লেখে না।

Usage:
    python3 scripts/progress.py status
    python3 scripts/progress.py next [N]
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_DIR_RE = re.compile(r"^\d\d-")
ROW_RE = re.compile(
    r"^\| (?P<id>L\d\d-\d\d) \| (?P<title>.+?) \| (?P<content>[A-Z_]+) \| (?P<learner>.+?) \|"
)
CONTENT_STATES = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED", "NEEDS_REVISION"}


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    content: str
    learner: str
    module_dir: str


def load_lessons(root: Path = ROOT) -> list[Lesson]:
    """সব module-এর PROGRESS.md থেকে lesson, curriculum ক্রমে।"""
    lessons: list[Lesson] = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and MODULE_DIR_RE.match(p.name)):
        progress = d / "PROGRESS.md"
        if not progress.is_file():
            continue
        for line in progress.read_text(encoding="utf-8").splitlines():
            m = ROW_RE.match(line)
            if m:
                lessons.append(Lesson(m["id"], m["title"], m["content"], m["learner"].strip(), d.name))
    return lessons


def validate(lessons: list[Lesson]) -> list[str]:
    """ID unique, ক্রম ঠিক, state বৈধ কিনা যাচাই।"""
    errors: list[str] = []
    seen: set[str] = set()
    for lesson in lessons:
        if lesson.id in seen:
            errors.append(f"duplicate id {lesson.id}")
        seen.add(lesson.id)
        if lesson.content not in CONTENT_STATES:
            errors.append(f"{lesson.id}: invalid content state {lesson.content}")
        if lesson.module_dir[:2] != lesson.id[1:3]:
            errors.append(f"{lesson.id}: listed in wrong module {lesson.module_dir}")
    ids = [lesson.id for lesson in lessons]
    if ids != sorted(ids):
        errors.append("lessons are not in curriculum order")
    return errors


def next_lessons(lessons: list[Lesson], n: int = 1) -> list[Lesson]:
    return [lesson for lesson in lessons if lesson.content != "COMPLETED"][:n]


def lesson_file(lesson: Lesson, root: Path = ROOT) -> Path | None:
    matches = sorted((root / lesson.module_dir).glob(f"{lesson.id}-*.md"))
    return matches[0] if matches else None


def cmd_status(lessons: list[Lesson]) -> None:
    done = sum(1 for lesson in lessons if lesson.content == "COMPLETED")
    print(f"Lessons: {done}/{len(lessons)} completed ({done / len(lessons):.1%})")
    by_module: dict[str, list[Lesson]] = {}
    for lesson in lessons:
        by_module.setdefault(lesson.module_dir, []).append(lesson)
    for module, items in by_module.items():
        c = sum(1 for lesson in items if lesson.content == "COMPLETED")
        if c:
            print(f"  {module:50} {c}/{len(items)}")
    nxt = next_lessons(lessons)
    if nxt:
        print(f"Next: {nxt[0].id} — {nxt[0].title}")


def cmd_next(lessons: list[Lesson], n: int) -> None:
    for lesson in next_lessons(lessons, n):
        path = lesson_file(lesson)
        where = path.relative_to(ROOT).as_posix() if path else f"{lesson.module_dir}/{lesson.id}-<slug>.md"
        print(f"{lesson.id}  [{lesson.content}]  {lesson.title}\n    {where}")


def main(argv: list[str] | None = None) -> int:
    # Windows console-এ বাংলা print করার জন্য
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p_next = sub.add_parser("next")
    p_next.add_argument("n", nargs="?", type=int, default=1)
    sub.add_parser("validate")
    args = parser.parse_args(argv)

    lessons = load_lessons()
    if not lessons:
        print("no lessons found", file=sys.stderr)
        return 1
    if args.cmd == "status":
        cmd_status(lessons)
    elif args.cmd == "next":
        cmd_next(lessons, args.n)
    else:
        errors = validate(lessons)
        for e in errors:
            print("ERROR", e)
        print(f"{len(lessons)} lessons checked, {len(errors)} errors")
        return 1 if errors else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
