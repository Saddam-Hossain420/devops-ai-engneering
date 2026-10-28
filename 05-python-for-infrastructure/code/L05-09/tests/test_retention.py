"""pytest-style tests for retention.py — চালানো: python3 -m pytest -v (L05-09 directory থেকে)

এখানে unittest-এর class লাগে না: সাধারণ function + `assert`; fixture argument-এর নাম দিয়ে আসে।
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

import retention as r

# ---------- unit: parametrize ----------

@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("db-20261027T0300Z.sql.gz", datetime(2026, 10, 27, 3, 0, tzinfo=UTC)),
        ("my-app-db-20240229T2359Z.tar.zst", datetime(2024, 2, 29, 23, 59, tzinfo=UTC)),   # leap day, prefix-এ '-'
        ("db-20261332T0300Z.sql.gz", None),         # মাস ১৩ — regex মেলে, তারিখ অসম্ভব
        ("db-20250229T0300Z.sql.gz", None),         # ২০২৫ leap year নয়
        ("db-20261027T0300.sql.gz", None),          # Z নেই — time zone অজানা
        ("db-latest.sql.gz", None),
        ("README.md", None),
    ],
)
def test_parse_name(name: str, expected: datetime | None) -> None:
    assert r.parse_name(name) == expected


@pytest.mark.parametrize(("daily", "weekly", "monthly", "kept"), [
    (7, 0, 0, 7),
    (0, 4, 0, 4),
    (0, 0, 3, 3),
    # daily ২১–২৭ অক্টো; weekly: ২৭, ২৫ (দুটোই daily-তে আছে), ১৮, ১১ → +২; monthly: ২৭, ৩০ সেপ্টে, ৩১ আগস্ট → +২
    (7, 4, 3, 11),      # বাকেট overlap করে — একই file একাধিক কারণে, গোনা একবার
    (0, 0, 0, 1),       # সব শূন্য হলেও newest থাকে
])
def test_counts(make_backups, now, daily: int, weekly: int, monthly: int, kept: int) -> None:
    paths = make_backups(days=100)
    result = r.plan(paths, now, daily, weekly, monthly)
    assert len(result.keep) == kept
    assert len(result.keep) + len(result.delete) == len(paths)


def test_newest_per_day_wins(make_backups, now) -> None:
    paths = make_backups(days=3, per_day=4)         # প্রতিদিন 03,04,05,06 টায়
    result = r.plan(paths, now, daily=3, weekly=0, monthly=0)
    assert sorted(p.name for p in result.keep) == [
        "db-20261025T0600Z.sql.gz", "db-20261026T0600Z.sql.gz", "db-20261027T0600Z.sql.gz"]


def test_iso_week_across_new_year() -> None:
    # ২০২৪-১২-৩০ (সোম) ও ২০২৫-০১-০৫ (রবি) একই ISO সপ্তাহ 2025-W01 — ক্যালেন্ডার বছর দিয়ে ভাগ করলে দুটি সপ্তাহ মনে হতো
    paths = [Path("db-20241230T0300Z.sql.gz"), Path("db-20250105T0300Z.sql.gz"), Path("db-20241229T0300Z.sql.gz")]
    result = r.plan(paths, datetime(2025, 1, 6, tzinfo=UTC), daily=0, weekly=2, monthly=0)
    assert set(result.keep) == {Path("db-20250105T0300Z.sql.gz"), Path("db-20241229T0300Z.sql.gz")}


# ---------- safety properties ----------

def test_future_backups_are_never_deleted(now) -> None:
    future = Path(f"db-{now + timedelta(hours=5):%Y%m%dT%H%MZ}.sql.gz")
    result = r.plan([future], now, 0, 0, 0)
    assert result.keep == {future: ["future"]}


def test_unrelated_files_are_ignored(tmp_path: Path, now) -> None:
    other = [tmp_path / "notes.txt", tmp_path / "db-latest.sql.gz"]
    result = r.plan(other, now)
    assert result.ignored == other
    assert result.delete == []


@pytest.mark.parametrize("days", [1, 2, 10, 400])
def test_never_deletes_newest(make_backups, now, days: int) -> None:
    paths = make_backups(days=days)
    newest = max(paths, key=lambda p: p.name)
    assert newest not in r.plan(paths, now, 0, 0, 0).delete


# ---------- integration: আসল filesystem, CLI ----------

@pytest.mark.integration
def test_cli_dry_run_then_delete(make_backups, now, tmp_path: Path, capsys) -> None:
    make_backups(days=30)
    (tmp_path / "keep-me.txt").write_text("not a backup")

    args = [str(tmp_path), "--daily", "7", "--weekly", "4", "--monthly", "2"]
    assert r.main(args, now=now) == 0
    out = capsys.readouterr().out
    assert "(dry-run)" in out
    assert len(list(tmp_path.iterdir())) == 31                    # dry-run কিছুই মোছেনি

    assert r.main([*args, "--delete"], now=now) == 0
    remaining = sorted(p.name for p in tmp_path.iterdir())
    assert "keep-me.txt" in remaining
    # ৭ daily + weekly-র বাড়তি ২ (১৮ ও ১১ অক্টো) + monthly-র বাড়তি ১ (৩০ সেপ্টে) + txt
    assert len(remaining) == 7 + 2 + 1 + 1


@pytest.mark.integration
def test_cli_bad_arguments(tmp_path: Path, capsys) -> None:
    assert r.main([str(tmp_path / "missing")]) == 2
    assert "error" in capsys.readouterr().err
