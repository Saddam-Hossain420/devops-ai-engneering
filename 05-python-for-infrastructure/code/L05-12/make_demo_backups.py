#!/usr/bin/env python3
"""make_demo_backups.py — verify_backup.py অনুশীলনের জন্য একটি ভালো ও ছয়টি নষ্ট backup বানায় (সব কৃত্রিম)।

  python3 make_demo_backups.py /tmp/backup-demo
  for f in /tmp/backup-demo/*.tar.gz; do python3 verify_backup.py "$f" --expect taskflow.db --sqlite taskflow.db; done

শুধু নির্দিষ্ট directory-তে লেখে; সেখানে আগে থেকে কিছু থাকলে থামে (কিছু overwrite করে না)।
"""
from __future__ import annotations

import hashlib
import io
import sqlite3
import sys
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

NOW = datetime.now(UTC)


def stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%MZ")


def make_db(path: Path, rows: int = 200) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, done INTEGER NOT NULL)")
    con.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", [(f"task {i}", i % 2) for i in range(rows)])
    con.commit()
    con.close()


def write_tar(dest: Path, files: dict[str, bytes]) -> None:
    with tarfile.open(dest, "w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mtime, info.mode = len(data), int(NOW.timestamp()), 0o600
            tar.addfile(info, io.BytesIO(data))


def sidecar(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 64
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        print(f"refusing: {out} is not empty", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp, "taskflow.db")
        make_db(db)
        db_bytes = db.read_bytes()
    config = b"[server]\nport = 8000\n"
    good = {"taskflow.db": db_bytes, "config/app.toml": config}

    def make(label: str, files: dict[str, bytes], when: datetime = NOW, checksum: bool = True) -> Path:
        p = out / f"{label}-{stamp(when - timedelta(hours=1))}.tar.gz"
        write_tar(p, files)
        if checksum:
            sidecar(p)
        return p

    make("01-good", good)
    p = make("02-truncated", good)                      # checksum বানানোর পরে কাটা — অর্ধেক upload-এর মতো
    p.write_bytes(p.read_bytes()[: p.stat().st_size // 2])
    p = make("03-bitflip", good)
    data = bytearray(p.read_bytes())
    data[len(data) // 2] ^= 0xFF
    p.write_bytes(bytes(data))
    make("04-traversal", {**good, "../../outside.txt": b"should never be written"})
    make("05-missing-db", {"config/app.toml": config})
    make("06-stale", good, when=NOW - timedelta(days=3))
    broken_db = bytearray(db_bytes)
    broken_db[4096:4096 + 200] = b"\x00" * 200           # দ্বিতীয় page নষ্ট — archive ঠিক, database নয়
    make("07-corrupt-db", {**good, "taskflow.db": bytes(broken_db)})
    for f in sorted(out.iterdir()):
        print(f.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
