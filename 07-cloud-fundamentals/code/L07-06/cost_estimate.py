#!/usr/bin/env python3
"""cost_estimate.py — architecture থেকে মাসিক খরচের আনুমানিক হিসাব, what-if ও budget alert-এর threshold।

  python3 cost_estimate.py taskflow-arch.json --prices example-prices.json
  python3 cost_estimate.py taskflow-arch.json --prices example-prices.json --schedule-dev 12x22

⚠️ example-prices.json-এর দাম উদাহরণ মাত্র — কোনো provider-এর আসল দাম নয়। আসল হিসাবের জন্য provider-এর
pricing page বা pricing calculator থেকে দাম বসান, এবং তারিখ ও region লিখে রাখুন। দাম সময়ের সাথে বদলায়।
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

HOURS_PER_MONTH = 730          # গড় (৮৭৬০ / ১২) — অনেক provider-ও এটা ব্যবহার করে


@dataclass
class Line:
    resource: str
    env: str
    item: str
    quantity: float
    unit: str
    unit_price: float

    @property
    def cost(self) -> float:
        return self.quantity * self.unit_price


def lines_for(arch: dict, prices: dict, dev_hours: float | None = None) -> list[Line]:
    out: list[Line] = []
    for r in arch["resources"]:
        env = r.get("env", "prod")
        count = r.get("count", 1)
        hours = r.get("hours", HOURS_PER_MONTH)
        if dev_hours is not None and env != "prod" and r.get("schedulable", True):
            hours = min(hours, dev_hours)
        kind = r["type"]
        if kind in prices.get("compute_per_hour", {}):
            out.append(Line(r["name"], env, f"compute {kind}", count * hours, "instance-hours",
                            prices["compute_per_hour"][kind]))
        elif kind != "none":
            raise KeyError(f"no price for type {kind!r}")
        for field, price_key, unit in (("storage_gb", "storage_gb_month", "GB-month"),
                                       ("snapshot_gb", "snapshot_gb_month", "GB-month"),
                                       ("egress_gb", "egress_gb", "GB"),
                                       ("nat_gb", "nat_processing_gb", "GB"),
                                       ("cross_az_gb", "cross_az_gb", "GB")):
            if r.get(field):
                out.append(Line(r["name"], env, field, r[field] * count if field in ("storage_gb", "snapshot_gb") else r[field],
                                unit, prices[price_key]))
        if r.get("nat_gateways"):
            out.append(Line(r["name"], env, "nat gateway hours", r["nat_gateways"] * HOURS_PER_MONTH, "hours",
                            prices["nat_gateway_per_hour"]))
    return out


def budget_alerts(total: float, thresholds: tuple[float, ...] = (0.5, 0.8, 1.0, 1.2)) -> list[tuple[str, float]]:
    return [(f"{int(t * 100)}%", round(total * t, 2)) for t in thresholds]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Estimate monthly cloud cost from an architecture description.")
    ap.add_argument("arch", type=Path)
    ap.add_argument("--prices", type=Path, required=True)
    ap.add_argument("--schedule-dev", metavar="HxD", help="non-prod runs H hours × D days per month, e.g. 12x22")
    a = ap.parse_args(argv)
    try:
        arch = json.loads(a.arch.read_text(encoding="utf-8"))
        prices = json.loads(a.prices.read_text(encoding="utf-8"))
        dev_hours = None
        if a.schedule_dev:
            h, d = (float(x) for x in a.schedule_dev.lower().split("x"))
            dev_hours = h * d
        lines = lines_for(arch, prices, dev_hours)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    cur = prices.get("currency", "?")
    if prices.get("_warning"):
        print(f"⚠️  {prices['_warning']}")
    print(f"{'resource':<14} {'env':<8} {'item':<28} {'quantity':>12} {'unit':<15} {'cost':>10}")
    for ln in sorted(lines, key=lambda x: -x.cost):
        print(f"{ln.resource:<14} {ln.env:<8} {ln.item:<28} {ln.quantity:>12.1f} {ln.unit:<15} {ln.cost:>10.2f}")
    total = sum(ln.cost for ln in lines)
    by_env: dict[str, float] = {}
    for ln in lines:
        by_env[ln.env] = by_env.get(ln.env, 0) + ln.cost
    print(f"\ntotal per month: {total:.2f} {cur}" + (f"   (non-prod scheduled {a.schedule_dev})" if a.schedule_dev else ""))
    print("by env: " + ", ".join(f"{e} {c:.2f}" for e, c in sorted(by_env.items())))
    top = max(lines, key=lambda x: x.cost)
    print(f"largest line: {top.resource} {top.item} — {top.cost / total:.0%} of the total")
    print("budget alerts (forecast-based): " + ", ".join(f"{p} → {v} {cur}" for p, v in budget_alerts(total)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
