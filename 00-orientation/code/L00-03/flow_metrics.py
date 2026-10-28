#!/usr/bin/env python3
"""Kanban flow metrics — work item-এর তারিখ থেকে cycle time, throughput, WIP ও Little's Law.

Input CSV columns:
  item_id, type, started, done
  - started: কাজ শুরুর তারিখ (YYYY-MM-DD)
  - done:    শেষের তারিখ; খালি = এখনো চলছে (WIP)
  - type:    feature / bug / chore (যেকোনো label)

Cycle time = done - started + 1 দিন (একই দিনে শুরু ও শেষ = ১ দিন)

Usage:
  python3 flow_metrics.py work_items.csv
  python3 flow_metrics.py work_items.csv --start 2026-09-01 --end 2026-09-30
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


@dataclass(frozen=True)
class Item:
    item_id: str
    type: str
    started: date
    done: date | None

    @property
    def cycle_days(self) -> int | None:
        return None if self.done is None else (self.done - self.started).days + 1


def parse_row(row: dict[str, str]) -> Item:
    started = date.fromisoformat(row["started"])
    done_raw = (row.get("done") or "").strip()
    done = date.fromisoformat(done_raw) if done_raw else None
    if done is not None and done < started:
        raise ValueError(f"{row['item_id']}: done is before started")
    return Item(row["item_id"], row["type"].strip(), started, done)


def load_items(path: Path) -> list[Item]:
    with path.open(newline="", encoding="utf-8") as f:
        return [parse_row(r) for r in csv.DictReader(f)]


def percentile(values: list[int], pct: float) -> int:
    """Nearest-rank percentile: সাজানো তালিকায় ceil(pct/100 × n)-তম মান."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def wip_on(items: list[Item], day: date) -> int:
    """নির্দিষ্ট দিনে কতগুলো item চলমান ছিল (শুরু হয়েছে, শেষ হয়নি বা সেদিনই শেষ)."""
    return sum(1 for i in items if i.started <= day and (i.done is None or i.done >= day))


def flow_metrics(items: list[Item], start: date, end: date) -> dict[str, float | int]:
    """[start, end] সময়সীমার flow metric."""
    if end < start:
        raise ValueError("end is before start")
    days = (end - start).days + 1
    finished = [i for i in items if i.done is not None and start <= i.done <= end]
    if not finished:
        raise ValueError("no items finished in the period")
    cycles = [i.cycle_days for i in finished]

    daily_wip = [wip_on(items, start + timedelta(days=d)) for d in range(days)]
    avg_wip = statistics.mean(daily_wip)
    throughput = len(finished) / days
    avg_cycle = statistics.mean(cycles)

    return {
        "period_days": days,
        "finished": len(finished),
        "throughput_per_day": round(throughput, 2),
        "cycle_time_avg_days": round(avg_cycle, 2),
        "cycle_time_p50_days": percentile(cycles, 50),
        "cycle_time_p85_days": percentile(cycles, 85),
        "avg_wip": round(avg_wip, 2),
        # Little's Law: avg WIP ≈ throughput × avg cycle time (stable system-এ)
        "littles_law_wip": round(throughput * avg_cycle, 2),
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Kanban flow metrics from a work-items CSV.")
    p.add_argument("csv_file", type=Path)
    p.add_argument("--start", type=date.fromisoformat, help="YYYY-MM-DD (default: প্রথম started)")
    p.add_argument("--end", type=date.fromisoformat, help="YYYY-MM-DD (default: শেষ done)")
    args = p.parse_args(argv)

    try:
        items = load_items(args.csv_file)
        if not items:
            raise ValueError("file has no items")
        start = args.start or min(i.started for i in items)
        end = args.end or max(i.done for i in items if i.done is not None)
        m = flow_metrics(items, start, end)
    except FileNotFoundError:
        print(f"error: file not found: {args.csv_file}", file=sys.stderr)
        return 2
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    open_items = sum(1 for i in items if i.done is None)
    print(f"Period                 : {start} → {end} ({m['period_days']} days)")
    print(f"Finished items         : {m['finished']}   (still open: {open_items})")
    print(f"Throughput             : {m['throughput_per_day']} items/day")
    print(f"Cycle time avg / p50   : {m['cycle_time_avg_days']} / {m['cycle_time_p50_days']} days")
    print(f"Cycle time p85         : {m['cycle_time_p85_days']} days  (৮৫% কাজ এর মধ্যে শেষ হয়)")
    print(f"Average WIP (measured) : {m['avg_wip']}")
    print(f"Little's Law WIP       : {m['littles_law_wip']}  (= throughput × avg cycle time)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
