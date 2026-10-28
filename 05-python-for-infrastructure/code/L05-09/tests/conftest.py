"""pytest-এর shared fixture — এই directory-র সব test file নিজে থেকে পায় (import লাগে না)।"""
from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))     # retention.py import করার জন্য

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)                   # সব test-এ একই "এখন" — নির্ভরযোগ্য


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def make_backups(tmp_path: Path) -> Callable[..., list[Path]]:
    """`make_backups(days=40)` → tmp_path-এ প্রতিদিন 03:00Z-এ একটি করে backup file (factory fixture)।"""

    def _make(days: int, prefix: str = "db", per_day: int = 1) -> list[Path]:
        paths = []
        for d in range(days):
            for h in range(per_day):
                ts = (NOW - timedelta(days=d)).replace(hour=3 + h, minute=0)
                p = tmp_path / f"{prefix}-{ts:%Y%m%dT%H%MZ}.sql.gz"
                p.write_bytes(b"x")
                paths.append(p)
        return paths

    return _make
