#!/usr/bin/env python3
"""Repository-র সব Markdown file-এ internal (relative) link-এর target আছে কিনা যাচাই করে।

External link (http/https/mailto) পরীক্ষা করে না — network ছাড়াই চলে।
Fenced code block ও inline code-এর ভেতরের link উপেক্ষা করে।

Usage:
    python3 scripts/check_links.py [ROOT]
Exit code: 0 = সব ঠিক, 1 = ভাঙা link আছে।
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")
# templates/-এ ইচ্ছাকৃত placeholder link থাকে (যেমন code/LMM-NN/example.py)
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "templates"}


def iter_markdown(root: Path):
    for path in sorted(root.rglob("*.md")):
        if not SKIP_DIRS.intersection(path.relative_to(root).parts):
            yield path


def extract_links(text: str) -> list[tuple[int, str]]:
    """(line number, target) — code block-এর বাইরের link।"""
    links: list[tuple[int, str]] = []
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in LINK_RE.finditer(INLINE_CODE_RE.sub("", line)):
            links.append((lineno, m.group(1)))
    return links


def broken_links(root: Path) -> list[str]:
    problems: list[str] = []
    for md in iter_markdown(root):
        for lineno, target in extract_links(md.read_text(encoding="utf-8")):
            if target.startswith(SKIP_PREFIXES):
                continue
            path_part = unquote(target.split("#", 1)[0])
            if not path_part:
                continue
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                problems.append(f"{md.relative_to(root).as_posix()}:{lineno}: {target}")
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    problems = broken_links(root)
    for p in problems:
        print("BROKEN", p)
    count = sum(1 for _ in iter_markdown(root))
    print(f"{count} markdown files checked, {len(problems)} broken links")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
