#!/usr/bin/env python3
"""verify_backup.py — backup আছে মানেই restore হবে না: archive, checksum, বয়স, বিষয়বস্তু ও আসল restore যাচাই।

  python3 verify_backup.py /var/backups/db/db-20261027T0300Z.tar.gz --max-age-h 26 --min-bytes 1024 \
      --expect taskflow.db --sqlite taskflow.db

ধাপ (প্রতিটির ফল আলাদা দেখানো হয়, প্রথম ব্যর্থতায় থামে না — যা যা ভুল সব জানা যায়):
  1. exists/size      2. age (নামের timestamp, না থাকলে mtime)
  3. checksum         পাশের <file>.sha256 থাকলে (sha256sum format) মেলানো
  4. archive          সব member পুরো পড়া — gzip CRC ও tar কাঠামো যাচাই; অনিরাপদ path ("../", absolute) ধরা
  5. contents         --expect-এর file গুলো আছে কিনা
  6. restore          temp directory-তে আসল extract (tarfile data filter) → --sqlite হলে PRAGMA integrity_check
Exit: 0 সব ঠিক, 2 কোনো ধাপ ব্যর্থ, 64 argument error। Temp directory সবসময় মুছে ফেলা হয়।
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import tarfile
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

STAMP = re.compile(r"(\d{8}T\d{4}Z)")


@dataclass
class Step:
    name: str
    ok: bool
    detail: str


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_time(path: Path) -> tuple[float, str]:
    m = STAMP.search(path.name)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%dT%H%MZ").replace(tzinfo=UTC).timestamp(), "name"
    return path.stat().st_mtime, "mtime"


def unsafe_member(name: str) -> bool:
    """`../x`, `/etc/x`, `C:x`, `\\x` — restore-এর সময় target directory-র বাইরে লিখতে পারে।"""
    p = PurePosixPath(name.replace("\\", "/"))
    if not p.parts:
        return True
    return p.is_absolute() or ".." in p.parts or ":" in p.parts[0]


def check_archive(path: Path) -> tuple[Step, list[str]]:
    names: list[str] = []
    try:
        with tarfile.open(path, "r:*") as tar:
            for member in tar:                              # streaming: প্রতিটি member-এর data পুরো পড়া
                names.append(member.name)
                if unsafe_member(member.name) or member.issym() or member.islnk():
                    return Step("archive", False, f"unsafe member {member.name!r}"), names
                if member.isfile():
                    f = tar.extractfile(member)
                    if f is not None:
                        while f.read(1 << 20):
                            pass
            # tarfile end-of-archive চিহ্নে থামে — compressed stream-এর শেষ (gzip-এর CRC-32 ও দৈর্ঘ্য) পড়ে না।
            # শেষ পর্যন্ত না পড়লে data-র মাঝের bit flip ধরা পড়ে না: নষ্ট byte নীরবে বেরিয়ে আসে।
            if tar.fileobj is not None:
                while tar.fileobj.read(1 << 20):
                    pass
    except (tarfile.TarError, EOFError, OSError) as exc:    # gzip CRC (BadGzipFile)/কাটা file এখানে ধরা পড়ে
        return Step("archive", False, f"{type(exc).__name__}: {exc}"), names
    return Step("archive", True, f"{len(names)} members readable"), names


def verify(path: Path, max_age_h: float, min_bytes: int, expect: list[str], sqlite_db: str | None,
           now: float | None = None) -> list[Step]:
    steps: list[Step] = []
    if not path.is_file():
        return [Step("exists", False, f"{path} not found")]
    size = path.stat().st_size
    steps.append(Step("size", size >= min_bytes, f"{size} bytes (min {min_bytes})"))

    taken, source = backup_time(path)
    age_h = ((now if now is not None else time.time()) - taken) / 3600
    steps.append(Step("age", 0 <= age_h <= max_age_h if source == "name" else age_h <= max_age_h,
                      f"{age_h:.1f} h old (from {source}; max {max_age_h} h)"))

    sidecar = path.with_name(path.name + ".sha256")
    if sidecar.is_file():
        expected = sidecar.read_text(encoding="utf-8").split()[0].lower()
        actual = sha256_of(path)
        steps.append(Step("checksum", actual == expected, "sha256 matches" if actual == expected
                          else f"sha256 mismatch: expected {expected[:12]}…, got {actual[:12]}…"))
    else:
        steps.append(Step("checksum", False, f"no {sidecar.name} next to the backup"))

    archive_step, names = check_archive(path)
    steps.append(archive_step)
    missing = [e for e in expect if e not in names]
    if not archive_step.ok:            # কাটা archive-এও আগের member-এর নাম পড়া যায় — "PASS" বিভ্রান্তিকর
        steps.append(Step("contents", False, f"not verified: archive unreadable (saw {len(names)} member names)"))
    else:
        steps.append(Step("contents", not missing, "all expected files present" if not missing
                          else f"missing: {', '.join(missing)}"))

    if archive_step.ok:
        with tempfile.TemporaryDirectory(prefix="restore-test-") as tmp:
            try:
                with tarfile.open(path, "r:*") as tar:
                    tar.extractall(tmp, filter="data")      # path traversal, device, setuid ইত্যাদি বাধা
                restored = sum(1 for p in Path(tmp).rglob("*") if p.is_file())
                steps.append(Step("restore", True, f"extracted {restored} files to a temp dir"))
                if sqlite_db:
                    steps.append(check_sqlite(Path(tmp) / sqlite_db))
            except (tarfile.TarError, OSError) as exc:
                steps.append(Step("restore", False, f"{type(exc).__name__}: {exc}"))
    else:
        steps.append(Step("restore", False, "skipped: archive unreadable"))
    return steps


def check_sqlite(db: Path) -> Step:
    if not db.is_file():
        return Step("sqlite", False, f"{db.name} not in archive")
    try:
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            result = con.execute("PRAGMA integrity_check").fetchone()[0]
            tables = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        return Step("sqlite", False, f"DatabaseError: {exc}")
    return Step("sqlite", result == "ok" and tables > 0, f"integrity_check={result}, tables={tables}")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Verify that a tar backup can really be restored.")
    ap.add_argument("backup", type=Path)
    ap.add_argument("--max-age-h", type=float, default=26.0)
    ap.add_argument("--min-bytes", type=int, default=1)
    ap.add_argument("--expect", action="append", default=[], metavar="MEMBER")
    ap.add_argument("--sqlite", metavar="MEMBER", help="restored SQLite file to integrity-check")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.max_age_h <= 0 or args.min_bytes < 0:
        print("error: --max-age-h must be > 0 and --min-bytes >= 0", file=sys.stderr)
        return 64
    steps = verify(args.backup, args.max_age_h, args.min_bytes, args.expect, args.sqlite)
    ok = all(s.ok for s in steps)
    if args.json:
        print(json.dumps({"backup": str(args.backup), "ok": ok, "steps": [asdict(s) for s in steps]}, indent=2))
    else:
        for s in steps:
            print(f"{'PASS' if s.ok else 'FAIL'}  {s.name:<9} {s.detail}")
        print(f"result: {'RESTORABLE' if ok else 'NOT VERIFIED'}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
