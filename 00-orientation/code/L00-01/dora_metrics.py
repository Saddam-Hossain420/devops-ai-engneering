#!/usr/bin/env python3
"""DORA metrics calculator — deployment record থেকে চারটি delivery metric হিসাব করে।

Metric:
  1. Deployment frequency          — প্রতিদিন গড়ে কতবার production-এ deploy
  2. Lead time for changes          — commit থেকে production পর্যন্ত সময় (median)
  3. Change failure rate            — কত শতাংশ deploy production-এ সমস্যা তৈরি করেছে
  4. Failed deployment recovery time — ব্যর্থ deploy থেকে service ঠিক হওয়া পর্যন্ত সময় (median)

Input CSV columns:
  deploy_id, commit_time, deploy_time, failed, restored_time
  - সময় ISO 8601 format-এ (যেমন 2026-10-01T10:00:00)
  - failed: yes / no
  - restored_time: শুধু failed=yes হলে

Usage:
  python3 dora_metrics.py deployments.csv
  python3 dora_metrics.py deployments.csv --json
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Deployment:
    deploy_id: str
    commit_time: datetime
    deploy_time: datetime
    failed: bool
    restored_time: datetime | None


def parse_row(row: dict[str, str]) -> Deployment:
    """একটি CSV row-কে Deployment-এ রূপান্তর; ভুল data হলে ValueError।"""
    failed_raw = row["failed"].strip().lower()
    if failed_raw not in {"yes", "no"}:
        raise ValueError(f"{row['deploy_id']}: failed must be yes/no, got {row['failed']!r}")
    failed = failed_raw == "yes"

    commit_time = datetime.fromisoformat(row["commit_time"])
    deploy_time = datetime.fromisoformat(row["deploy_time"])
    if deploy_time < commit_time:
        raise ValueError(f"{row['deploy_id']}: deploy_time is before commit_time")

    restored_raw = (row.get("restored_time") or "").strip()
    restored_time = datetime.fromisoformat(restored_raw) if restored_raw else None
    if failed and restored_time is None:
        raise ValueError(f"{row['deploy_id']}: failed deployment needs restored_time")
    if restored_time is not None and restored_time < deploy_time:
        raise ValueError(f"{row['deploy_id']}: restored_time is before deploy_time")

    return Deployment(row["deploy_id"], commit_time, deploy_time, failed, restored_time)


def load_deployments(path: Path) -> list[Deployment]:
    with path.open(newline="", encoding="utf-8") as f:
        return [parse_row(row) for row in csv.DictReader(f)]


def hours(delta) -> float:
    return delta.total_seconds() / 3600


def compute_metrics(deployments: list[Deployment]) -> dict[str, float | int]:
    """চারটি DORA metric। Deployment না থাকলে ValueError।"""
    if not deployments:
        raise ValueError("no deployments")

    first = min(d.deploy_time for d in deployments)
    last = max(d.deploy_time for d in deployments)
    # একই দিনের সব deploy হলেও অন্তত ১ দিন ধরা — শূন্য দিয়ে ভাগ এড়াতে
    window_days = max((last - first).total_seconds() / 86400, 1.0)

    lead_times = [hours(d.deploy_time - d.commit_time) for d in deployments]
    failures = [d for d in deployments if d.failed]
    recovery_times = [hours(d.restored_time - d.deploy_time) for d in failures if d.restored_time]

    return {
        "deployments": len(deployments),
        "window_days": round(window_days, 2),
        "deployment_frequency_per_day": round(len(deployments) / window_days, 2),
        # median ব্যবহার: একটি অস্বাভাবিক ধীর change গড়কে বিকৃত করে, median করে না
        "lead_time_median_hours": round(statistics.median(lead_times), 2),
        "change_failure_rate_percent": round(100 * len(failures) / len(deployments), 1),
        "recovery_time_median_hours": round(statistics.median(recovery_times), 2) if recovery_times else 0.0,
    }


def render_text(m: dict[str, float | int]) -> str:
    return "\n".join([
        f"Deployments analysed            : {m['deployments']} (window {m['window_days']} days)",
        f"Deployment frequency            : {m['deployment_frequency_per_day']} per day",
        f"Lead time for changes (median)  : {m['lead_time_median_hours']} hours",
        f"Change failure rate             : {m['change_failure_rate_percent']} %",
        f"Failed deploy recovery (median) : {m['recovery_time_median_hours']} hours",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute DORA metrics from a deployments CSV.")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        metrics = compute_metrics(load_deployments(args.csv_file))
    except FileNotFoundError:
        print(f"error: file not found: {args.csv_file}", file=sys.stderr)
        return 2
    except (KeyError, ValueError) as exc:
        print(f"error: invalid data: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(metrics, indent=2) if args.json else render_text(metrics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
