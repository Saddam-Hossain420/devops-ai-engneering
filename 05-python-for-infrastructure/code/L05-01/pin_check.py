#!/usr/bin/env python3
"""pin_check.py — dependency কতটা পুনরুৎপাদনযোগ্যভাবে নির্দিষ্ট: requirements.txt ও pyproject.toml।

  python3 pin_check.py requirements.txt
  python3 pin_check.py pyproject.toml --mode library     # library-তে range স্বাভাবিক; শুধু অনুপস্থিত সীমা সতর্কতা

শ্রেণি: pinned (==x.y.z), hashed (--hash সহ), range (>=, ~=, <), unpinned (শুধু নাম), url (git+/http),
include (-r/-c), editable (-e)।
Exit: 0 OK, 1 application-mode-এ unpinned/range আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None

NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(.*)$")


@dataclass
class Dep:
    line: int
    raw: str
    name: str
    kind: str


def classify(spec: str, hashed: bool) -> str:
    spec = spec.split(";", 1)[0].strip()          # environment marker বাদ
    if re.fullmatch(r"==\s*[0-9][^,*\s]*", spec):
        return "hashed" if hashed else "pinned"
    if not spec:
        return "unpinned"
    return "range"


def parse_requirements(text: str) -> list[Dep]:
    deps, pending, start = [], "", 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split(" #", 1)[0].rstrip()
        if not pending:
            start = n
        if line.endswith("\\"):                      # continuation (hash-এর লাইন প্রায়ই এভাবে)
            pending += line[:-1] + " "
            continue
        line = (pending + line).strip()
        pending = ""
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-r ", "-c ", "--requirement", "--constraint")):
            deps.append(Dep(start, line, line.split()[-1], "include"))
            continue
        if line.startswith(("-e ", "--editable")):
            deps.append(Dep(start, line, line.split()[-1], "editable"))
            continue
        if line.startswith("-"):                    # --index-url ইত্যাদি
            continue
        if "://" in line or line.startswith("git+"):
            deps.append(Dep(start, line, line, "url"))
            continue
        hashed = "--hash=" in line
        req = line.split("--hash=", 1)[0].strip()
        m = NAME.match(req)
        if not m:
            raise ValueError(f"line {start}: cannot parse {raw!r}")
        deps.append(Dep(start, line, m.group(1).lower(), classify(m.group(3), hashed)))
    return deps


def parse_pyproject(text: str) -> list[Dep]:
    if tomllib is None:
        raise ValueError("tomllib needs Python 3.11+")
    project = tomllib.loads(text).get("project", {})
    deps = []
    for i, req in enumerate(project.get("dependencies", []), 1):
        m = NAME.match(req.strip())
        if not m:
            raise ValueError(f"dependency {i}: cannot parse {req!r}")
        deps.append(Dep(i, req, m.group(1).lower(), classify(m.group(3), False)))
    return deps


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Check how reproducibly dependencies are pinned.")
    ap.add_argument("file", type=Path)
    ap.add_argument("--mode", choices=["application", "library"], default="application")
    args = ap.parse_args(argv)
    try:
        text = args.file.read_text(encoding="utf-8")
        deps = parse_pyproject(text) if args.file.suffix == ".toml" else parse_requirements(text)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    bad = []
    for d in deps:
        if args.mode == "application":
            flag = d.kind in ("unpinned", "range", "url", "editable")
        else:
            flag = d.kind == "unpinned"           # library: range ঠিক, কিন্তু কোনো সীমাই নেই — সতর্কতা
        mark = "WARN" if flag else "ok  "
        print(f"{mark} line {d.line:<3} {d.kind:9} {d.name}")
        if flag:
            bad.append(d)
    kinds = {k: sum(d.kind == k for d in deps) for k in ("hashed", "pinned", "range", "unpinned", "url", "editable", "include")}
    print("summary: " + ", ".join(f"{k}={v}" for k, v in kinds.items() if v))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
