#!/usr/bin/env python3
"""ce_report.py — Cost Explorer-এর `get-cost-and-usage` output থেকে service ও tag অনুযায়ী খরচ, untagged অংশ (offline)।

  aws ce get-cost-and-usage --time-period Start=2026-09-01,End=2026-11-01 --granularity MONTHLY \
      --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE > by-service.json
  aws ce get-cost-and-usage … --group-by Type=TAG,Key=Project > by-project.json
  python3 ce_report.py by-service.json by-project.json

মনে রাখুন: Cost Explorer API-র প্রতিটি request চার্জযোগ্য (pricing page); tag দিয়ে ভাগ করতে tag-টি Billing-এ
"cost allocation tag" হিসেবে চালু করতে হয়, এবং চালুর আগের খরচে tag থাকে না।
Tag-group-এর key `Project$lab08`; `Project$` (খালি মান) = সেই tag ছাড়া খরচ।
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


def totals(doc: dict[str, Any], metric: str = "UnblendedCost") -> tuple[list[str], dict[str, list[float]], str]:
    """(period-এর শুরু, {group: [প্রতি period-এর খরচ]}, unit)।"""
    periods = [r["TimePeriod"]["Start"] for r in doc["ResultsByTime"]]
    out: dict[str, list[float]] = defaultdict(lambda: [0.0] * len(periods))
    unit = "?"
    for i, r in enumerate(doc["ResultsByTime"]):
        for g in r.get("Groups", []):
            m = g["Metrics"][metric]
            out[" / ".join(g["Keys"])][i] += float(m["Amount"])
            unit = m.get("Unit", unit)
    return periods, dict(out), unit


def report(doc: dict[str, Any], top: int = 5) -> list[str]:
    periods, groups, unit = totals(doc)
    last = len(periods) - 1
    total = sum(v[last] for v in groups.values())
    lines = [f"period {periods[last]}: total {total:.2f} {unit}"]
    for name, vals in sorted(groups.items(), key=lambda kv: -kv[1][last])[:top]:
        share = 100 * vals[last] / total if total else 0
        change = ""
        if last > 0 and vals[last - 1] > 0:
            change = f"  ({100 * (vals[last] - vals[last - 1]) / vals[last - 1]:+.0f}% vs {periods[last - 1]})"
        elif last > 0 and vals[last] > 0:
            change = "  (new)"
        label = name if not name.endswith("$") else f"{name}  ← UNTAGGED"
        lines.append(f"  {vals[last]:>9.2f}  {share:5.1f}%  {label}{change}")
    untagged = sum(v[last] for k, v in groups.items() if k.endswith("$"))
    if any("$" in k for k in groups) and total:
        lines.append(f"untagged: {untagged:.2f} {unit} = {100 * untagged / total:.0f}% of the period"
                     + (" — find owners (tag_audit.py, inventory.py)" if untagged / total > 0.1 else ""))
    return lines


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Summarize Cost Explorer get-cost-and-usage output (offline).")
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args(argv)
    try:
        for f in a.files:
            doc = json.loads(f.read_text(encoding="utf-8"))
            print(f"== {f.name}" + (f"  [{doc['_note']}]" if "_note" in doc else ""))
            for line in report(doc, a.top):
                print(line)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
