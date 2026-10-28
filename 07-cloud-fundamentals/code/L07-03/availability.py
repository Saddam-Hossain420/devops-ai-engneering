#!/usr/bin/env python3
"""availability.py — একটি architecture-এর প্রত্যাশিত availability, AZ-এর correlated ব্যর্থতা সহ; single point of failure খোঁজা।

  python3 availability.py single-vm.json
  python3 availability.py two-az.json --simulate 200000
  python3 availability.py same-az-pair.json --compare-naive

Model: system চালু = প্রতিটি tier-এ অন্তত min_healthy instance চালু। Instance চালু = নিজে চালু AND তার AZ চালু।
একই AZ-এর সব instance একসাথে পড়ে (correlated)। বিশ্লেষণ: সব AZ-অবস্থা (2^k) গুনে, প্রতিটিতে tier-এর binomial।
সংখ্যাগুলো (instance/AZ availability) input-এর অনুমান — কোনো provider-এর SLA নয়।
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

MINUTES_PER_YEAR = 365.25 * 24 * 60


@dataclass
class Tier:
    name: str
    availability: float          # একটি instance-এর
    azs: list[str]               # প্রতিটি instance কোন AZ-এ
    min_healthy: int = 1


@dataclass
class Spec:
    name: str
    az_availability: float
    tiers: list[Tier]


def load(path: Path) -> Spec:
    d = json.loads(path.read_text(encoding="utf-8"))
    tiers = [Tier(t["name"], t["availability"], t["azs"], t.get("min_healthy", 1)) for t in d["tiers"]]
    for t in tiers:
        if not 0 < t.availability <= 1 or not 1 <= t.min_healthy <= len(t.azs):
            raise ValueError(f"tier {t.name}: availability in (0,1] and 1 <= min_healthy <= instances")
    return Spec(d["name"], d["az_availability"], tiers)


def tier_up_prob(tier: Tier, az_up: dict[str, bool]) -> float:
    """AZ-অবস্থা জানা থাকলে tier-এ ≥ min_healthy instance চালু থাকার সম্ভাবনা (binomial, শুধু চালু AZ-এর instance)।"""
    n = sum(1 for az in tier.azs if az_up[az])
    a = tier.availability
    return sum(math.comb(n, k) * a**k * (1 - a) ** (n - k) for k in range(tier.min_healthy, n + 1))


def analytic(spec: Spec) -> float:
    azs = sorted({az for t in spec.tiers for az in t.azs})
    total = 0.0
    for states in itertools.product([True, False], repeat=len(azs)):
        az_up = dict(zip(azs, states, strict=True))
        p_state = math.prod(spec.az_availability if up else 1 - spec.az_availability for up in states)
        total += p_state * math.prod(tier_up_prob(t, az_up) for t in spec.tiers)
    return total


def naive(spec: Spec) -> float:
    """প্রচলিত কিন্তু ভুল-প্রবণ হিসাব: instance-গুলো স্বাধীন ধরে (AZ-কে instance-এর availability-তে গুণ করে)।"""
    result = 1.0
    for t in spec.tiers:
        a = t.availability * spec.az_availability
        n = len(t.azs)
        result *= sum(math.comb(n, k) * a**k * (1 - a) ** (n - k) for k in range(t.min_healthy, n + 1))
    return result


def simulate(spec: Spec, trials: int, seed: int = 1) -> float:
    rng = random.Random(seed)
    azs = sorted({az for t in spec.tiers for az in t.azs})
    up_count = 0
    for _ in range(trials):
        az_up = {az: rng.random() < spec.az_availability for az in azs}
        ok = True
        for t in spec.tiers:
            healthy = sum(1 for az in t.azs if az_up[az] and rng.random() < t.availability)
            if healthy < t.min_healthy:
                ok = False
                break
        up_count += ok
    return up_count / trials


def single_points(spec: Spec) -> list[str]:
    out = []
    for t in spec.tiers:
        if len(t.azs) == t.min_healthy:
            out.append(f"{t.name}: {len(t.azs)} instance(s), all needed — any instance failure is an outage")
        elif len(set(t.azs)) == 1:
            out.append(f"{t.name}: all {len(t.azs)} instances in AZ {t.azs[0]} — one AZ failure takes the tier down")
        else:
            per_az = {az: t.azs.count(az) for az in set(t.azs)}
            worst = max(per_az.values())
            if len(t.azs) - worst < t.min_healthy:
                out.append(f"{t.name}: losing the biggest AZ ({worst} instances) leaves fewer than min_healthy={t.min_healthy}")
    return out


def fmt_downtime(a: float) -> str:
    minutes = (1 - a) * MINUTES_PER_YEAR
    return f"{minutes / 60:.1f} h/year" if minutes >= 120 else f"{minutes:.0f} min/year"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Availability with correlated AZ failures.")
    ap.add_argument("specs", nargs="+", type=Path)
    ap.add_argument("--simulate", type=int, default=0, help="Monte Carlo trials to cross-check")
    ap.add_argument("--compare-naive", action="store_true")
    a = ap.parse_args(argv)
    for path in a.specs:
        try:
            spec = load(path)
        except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            return 2
        av = analytic(spec)
        print(f"{spec.name}: availability {av:.6f} ({av * 100:.4f}%) ≈ downtime {fmt_downtime(av)}")
        if a.compare_naive:
            nv = naive(spec)
            diff = (nv - av) * MINUTES_PER_YEAR
            direction = "optimistic" if diff > 0 else "pessimistic" if diff < 0 else "equal"
            print(f"  naive (independent instances): {nv:.6f} ≈ {fmt_downtime(nv)}"
                  f"  ← {direction} by {abs(diff):.0f} min/year (ignores which AZ each instance is in)")
        if a.simulate:
            sim = simulate(spec, a.simulate)
            print(f"  monte carlo ({a.simulate} trials): {sim:.6f}")
        for spf in single_points(spec):
            print(f"  SPOF: {spf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
