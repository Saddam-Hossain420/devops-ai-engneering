#!/usr/bin/env python3
"""healthcheck.py — একাধিক check সমান্তরালে: HTTP, TCP, disk, file freshness; সামগ্রিক deadline; JSON ও exit code।

  python3 healthcheck.py checks.json
  python3 healthcheck.py checks.json --json --deadline 10

checks.json:
  [{"name": "api", "type": "http", "url": "http://127.0.0.1:8000/health", "expect_status": 200,
    "contains": "ok", "warn_ms": 300, "timeout": 3},
   {"name": "db", "type": "tcp", "host": "127.0.0.1", "port": 5432, "timeout": 2},
   {"name": "root-disk", "type": "disk", "path": "/", "warn": 80, "crit": 90},
   {"name": "backup-fresh", "type": "file_age", "path": "/var/backups/db/latest.tar.gz", "warn_h": 26, "crit_h": 50}]

Exit (L05-08-এর মতো): 0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN; config ভুল হলে 64।
"""
from __future__ import annotations

import argparse
import json
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3
NAMES = {OK: "ok", WARNING: "warning", CRITICAL: "critical", UNKNOWN: "unknown"}
SEVERITY = {OK: 0, WARNING: 1, UNKNOWN: 2, CRITICAL: 3}
EX_CONFIG = 64


@dataclass
class Result:
    name: str
    type: str
    status: int
    detail: str
    duration_ms: float = 0.0


def check_http(c: dict[str, Any]) -> tuple[int, str]:
    start = time.monotonic()
    req = urllib.request.Request(c["url"], headers={"User-Agent": "healthcheck/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=c.get("timeout", 5)) as resp:
            status, body = resp.status, resp.read(65536).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        with exc:
            status, body = exc.code, ""
    ms = (time.monotonic() - start) * 1000
    if status != c.get("expect_status", 200):
        return CRITICAL, f"HTTP {status} (expected {c.get('expect_status', 200)})"
    if c.get("contains") and c["contains"] not in body:
        return CRITICAL, f"HTTP {status} but body lacks {c['contains']!r}"
    if c.get("warn_ms") and ms > c["warn_ms"]:
        return WARNING, f"HTTP {status} slow: {ms:.0f} ms > {c['warn_ms']} ms"
    return OK, f"HTTP {status} in {ms:.0f} ms"


def check_tcp(c: dict[str, Any]) -> tuple[int, str]:
    with socket.create_connection((c["host"], int(c["port"])), timeout=c.get("timeout", 3)):
        return OK, f"{c['host']}:{c['port']} open"


def check_disk(c: dict[str, Any]) -> tuple[int, str]:
    u = shutil.disk_usage(c["path"])
    used = 100 * (u.total - u.free) / u.total
    status = CRITICAL if used >= c.get("crit", 90) else WARNING if used >= c.get("warn", 80) else OK
    return status, f"{used:.1f}% used"


def check_file_age(c: dict[str, Any]) -> tuple[int, str]:
    age_h = (time.time() - Path(c["path"]).stat().st_mtime) / 3600
    status = CRITICAL if age_h >= c.get("crit_h", 50) else WARNING if age_h >= c.get("warn_h", 26) else OK
    return status, f"modified {age_h:.1f} h ago"


CHECKS: dict[str, Callable[[dict[str, Any]], tuple[int, str]]] = {
    "http": check_http, "tcp": check_tcp, "disk": check_disk, "file_age": check_file_age,
}
REQUIRED = {"http": ["url"], "tcp": ["host", "port"], "disk": ["path"], "file_age": ["path"]}


def validate(config: object) -> list[str]:
    if not isinstance(config, list):
        return ["config must be a JSON list of checks"]
    errors, names = [], set()
    for i, c in enumerate(config):
        if not isinstance(c, dict):
            errors.append(f"check #{i}: must be an object")
            continue
        name, kind = c.get("name"), c.get("type")
        if not name or name in names:
            errors.append(f"check #{i}: missing or duplicate name {name!r}")
        names.add(name)
        if kind not in CHECKS:
            errors.append(f"{name}: unknown type {kind!r} (known: {', '.join(CHECKS)})")
            continue
        errors += [f"{name}: missing {field!r}" for field in REQUIRED[kind] if field not in c]
    return errors


def run_one(c: dict[str, Any]) -> Result:
    start = time.monotonic()
    try:
        status, detail = CHECKS[c["type"]](c)
    except TimeoutError:
        status, detail = CRITICAL, f"timeout after {c.get('timeout', '?')}s"
    except (OSError, urllib.error.URLError, ValueError) as exc:
        reason = getattr(exc, "reason", None) or getattr(exc, "strerror", None) or str(exc)
        status, detail = CRITICAL, f"{type(exc).__name__}: {reason}"
    except Exception as exc:                          # check-এর bug যেন পুরো run না থামায়
        status, detail = UNKNOWN, f"check crashed: {type(exc).__name__}: {exc}"
    return Result(c["name"], c["type"], status, detail, round((time.monotonic() - start) * 1000, 1))


def run_all(config: list[dict[str, Any]], deadline: float, workers: int = 8) -> list[Result]:
    """সব check সমান্তরালে; deadline পেরোলে যেগুলো শেষ হয়নি সেগুলো UNKNOWN (অপেক্ষা নয়)।

    ThreadPoolExecutor নয়: তার worker thread non-daemon, interpreter বন্ধের সময় (atexit) সেগুলোর শেষের
    অপেক্ষা করে — ফলে আটকে থাকা check থাকলে deadline-এর পরেও process বের হয় না (Section 9.4)।
    """
    results: dict[str, Result] = {}
    slots = threading.BoundedSemaphore(workers)

    def worker(c: dict[str, Any]) -> None:
        with slots:
            results[c["name"]] = run_one(c)

    threads = [threading.Thread(target=worker, args=(c,), daemon=True, name=f"check-{c['name']}") for c in config]
    for t in threads:
        t.start()
    end = time.monotonic() + deadline
    for t in threads:
        t.join(max(0.0, end - time.monotonic()))
    for c in config:
        if c["name"] not in results:
            results[c["name"]] = Result(c["name"], c["type"], UNKNOWN, f"not finished within deadline {deadline}s")
    return [results[c["name"]] for c in config]              # config-এর ক্রমে


def worst(results: list[Result]) -> int:
    return max((r.status for r in results), key=SEVERITY.__getitem__, default=UNKNOWN)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Run health checks in parallel.")
    ap.add_argument("config", type=Path)
    ap.add_argument("--deadline", type=float, default=15.0, help="overall seconds (default 15)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {args.config}: {exc}", file=sys.stderr)
        return EX_CONFIG
    errors = validate(config)
    if errors:
        for e in errors:
            print(f"config error: {e}", file=sys.stderr)
        return EX_CONFIG
    start = time.monotonic()
    results = run_all(config, args.deadline)
    overall = worst(results)
    total_ms = round((time.monotonic() - start) * 1000, 1)
    if args.json:
        print(json.dumps({"status": NAMES[overall], "duration_ms": total_ms,
                          "checks": [{**asdict(r), "status": NAMES[r.status]} for r in results]}, indent=2))
    else:
        for r in results:
            print(f"{NAMES[r.status].upper():<9} {r.name:<16} {r.detail}  ({r.duration_ms} ms)")
        print(f"overall: {NAMES[overall].upper()} in {total_ms} ms")
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
