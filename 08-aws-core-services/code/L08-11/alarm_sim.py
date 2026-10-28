#!/usr/bin/env python3
"""alarm_sim.py — CloudWatch alarm-এর "M out of N" মূল্যায়ন ও TreatMissingData একটি datapoint-ধারায় চালিয়ে দেখা।

  python3 alarm_sim.py --series 1,2,9,9,2,9,9,9,-,-,- --threshold 5 --n 3 --m 2 --missing missing

`-` = সেই period-এ data নেই। প্রতিটি period-এর শেষে শেষ N period দেখে state: OK / ALARM / INSUFFICIENT_DATA।
এটা **শেখার জন্য সরল মডেল**: যথেষ্ট প্রমাণ না থাকলে আগের state থাকে; সব missing হলে `missing` → INSUFFICIENT_DATA,
`ignore` → আগের state। `missing` ও `ignore`-এর ক্ষেত্রে
AWS প্রয়োজনে আরও পেছনের datapoint দেখতে পারে (documentation-এর table) — এখানে শুধু শেষ N period।
"""
from __future__ import annotations

import argparse
import sys

COMPARE = {
    "GreaterThanThreshold": lambda v, t: v > t,
    "GreaterThanOrEqualToThreshold": lambda v, t: v >= t,
    "LessThanThreshold": lambda v, t: v < t,
    "LessThanOrEqualToThreshold": lambda v, t: v <= t,
}
MISSING = ("missing", "ignore", "breaching", "notBreaching")


def evaluate(series: list[float | None], threshold: float, n: int, m: int, missing: str,
             op: str = "GreaterThanOrEqualToThreshold") -> list[str]:
    if not 1 <= m <= n:
        raise ValueError("need 1 <= M (datapoints to alarm) <= N (evaluation periods)")
    if missing not in MISSING:
        raise ValueError(f"TreatMissingData must be one of {MISSING}")
    cmp = COMPARE[op]
    states: list[str] = []
    state = "INSUFFICIENT_DATA"
    for i in range(len(series)):
        window = series[max(0, i - n + 1): i + 1]
        if missing == "breaching":
            flags = [v is None or cmp(v, threshold) for v in window]
        elif missing == "notBreaching":
            flags = [v is not None and cmp(v, threshold) for v in window]
        else:
            present = [v for v in window if v is not None]
            if not present:
                state = "INSUFFICIENT_DATA" if missing == "missing" else state
                states.append(state)
                continue
            flags = [cmp(v, threshold) for v in present]
        breaching, fine = sum(flags), len(flags) - sum(flags)
        if breaching >= m:
            state = "ALARM"
        elif fine > n - m:                 # বাকি সব breaching হলেও M-এ পৌঁছানো অসম্ভব — নিশ্চিতভাবে OK
            state = "OK"
        # নইলে প্রমাণ যথেষ্ট নয় — আগের state থাকে (শুরুতে INSUFFICIENT_DATA)
        states.append(state)
    return states


def parse_series(text: str) -> list[float | None]:
    return [None if x.strip() in ("-", "") else float(x) for x in text.split(",")]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Simulate CloudWatch alarm evaluation (simplified).")
    ap.add_argument("--series", required=True, help="comma-separated values per period, '-' = missing")
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--n", type=int, required=True, help="EvaluationPeriods")
    ap.add_argument("--m", type=int, required=True, help="DatapointsToAlarm")
    ap.add_argument("--missing", default="missing", choices=MISSING)
    ap.add_argument("--op", default="GreaterThanOrEqualToThreshold", choices=sorted(COMPARE))
    ap.add_argument("--period", type=int, default=60)
    a = ap.parse_args(argv)
    try:
        series = parse_series(a.series)
        states = evaluate(series, a.threshold, a.n, a.m, a.missing, a.op)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"{a.m} of {a.n} periods {a.op} {a.threshold:g}, TreatMissingData={a.missing}, period {a.period}s")
    prev = None
    for i, (v, s) in enumerate(zip(series, states, strict=True)):
        mark = "  ← changed" if s != prev and prev is not None else ""
        print(f"  t={(i + 1) * a.period:>5}s  value={'-' if v is None else f'{v:g}':>6}  {s}{mark}")
        prev = s
    first = next((i for i, s in enumerate(states) if s == "ALARM"), None)
    if first is not None:
        print(f"first ALARM after {(first + 1) * a.period}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
