#!/usr/bin/env python3
"""envcheck.py — বর্তমান Python environment কেমন: version, venv, PEP 668, pip, installed package।

  python3 envcheck.py                         # মানুষের পড়ার মতো
  python3 envcheck.py --json                  # automation
  python3 envcheck.py --requires ">=3.10"     # minimum version যাচাই (বা --pyproject pyproject.toml)

Exit: 0 OK, 1 শর্ত পূরণ হয়নি (version কম, বা --require-venv অথচ venv নয়), 2 input error।
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import sysconfig
from importlib import metadata
from pathlib import Path

try:
    import tomllib  # Python ৩.১১+
except ModuleNotFoundError:         # pragma: no cover — ৩.১০
    tomllib = None


def in_venv() -> bool:
    """venv-এ sys.prefix (venv) আর sys.base_prefix (মূল Python) ভিন্ন।"""
    return sys.prefix != sys.base_prefix


def externally_managed() -> Path | None:
    """PEP 668: distribution-এর Python-এ stdlib directory-তে EXTERNALLY-MANAGED file — তখন সরাসরি pip install নিষেধ।"""
    marker = Path(sysconfig.get_path("stdlib")) / "EXTERNALLY-MANAGED"
    return marker if marker.exists() else None


def parse_min_version(spec: str) -> tuple[int, ...]:
    """'>=3.10' বা '>=3.10,<4' থেকে নিম্নসীমা।"""
    m = re.search(r">=\s*(\d+(?:\.\d+)*)", spec)
    if not m:
        raise ValueError(f"no '>=' lower bound in {spec!r}")
    return tuple(int(x) for x in m.group(1).split("."))


def requires_from_pyproject(path: Path) -> str:
    if tomllib is None:
        raise ValueError("tomllib needs Python 3.11+")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    spec = data.get("project", {}).get("requires-python")
    if not spec:
        raise ValueError(f"{path}: [project].requires-python not set")
    return spec


def report() -> dict:
    pip_version = None
    try:
        pip_version = metadata.version("pip")
    except metadata.PackageNotFoundError:
        pass
    dists = sorted({(d.metadata["Name"] or "?").lower() for d in metadata.distributions()})
    em = externally_managed()
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
        "in_venv": in_venv(),
        "prefix": sys.prefix,
        "base_prefix": sys.base_prefix,
        "externally_managed": str(em) if em else None,
        "pip": pip_version,
        "installed_count": len(dists),
        "installed_sample": dists[:10],
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Describe the current Python environment.")
    ap.add_argument("--json", action="store_true")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--requires", help="version specifier, e.g. '>=3.10'")
    g.add_argument("--pyproject", type=Path, help="read [project].requires-python from this file")
    ap.add_argument("--require-venv", action="store_true", help="fail if not inside a virtual environment")
    args = ap.parse_args(argv)
    r = report()
    problems = []
    try:
        spec = args.requires or (requires_from_pyproject(args.pyproject) if args.pyproject else None)
        if spec:
            need = parse_min_version(spec)
            have = tuple(sys.version_info[: len(need)])
            r["requires"] = spec
            if have < need:
                problems.append(f"python {r['python']} does not satisfy {spec}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.require_venv and not r["in_venv"]:
        problems.append("not inside a virtual environment (python3 -m venv .venv && . .venv/bin/activate)")
    r["problems"] = problems
    if args.json:
        print(json.dumps(r, indent=2))
    else:
        for k in ("python", "implementation", "executable", "in_venv", "prefix", "base_prefix",
                  "externally_managed", "pip", "installed_count"):
            print(f"{k:20} {r[k]}")
        for p in problems:
            print(f"PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
