#!/usr/bin/env python3
"""Lab 07-B verification — on-prem বনাম cloud তুলনার folder যাচাই (offline)।

  python3 check_b.py ~/lab07b --prices ../../../07-cloud-fundamentals/code/L07-06/example-prices.json

Folder-এ লাগবে: onprem-avail.json, cloud-avail.json (L07-03-এর availability spec), cloud-arch.json (L07-06-এর
architecture), comparison.json, decision.md। Checker availability ও খরচ নিজে আবার হিসাব করে comparison.json-এর
সংখ্যার সাথে মেলায় — অর্থাৎ সংখ্যাগুলো tool চালিয়ে পাওয়া, অনুমানে লেখা নয়।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "07-cloud-fundamentals" / "code" / "L07-03"))
sys.path.insert(0, str(REPO / "07-cloud-fundamentals" / "code" / "L07-06"))
import availability as av  # noqa: E402
import cost_estimate as ce  # noqa: E402

HEADINGS = ("## Decision", "## Risks", "## What would change my mind")


def downtime_min(a: float) -> float:
    return (1 - a) * av.MINUTES_PER_YEAR


def close(got: float, want: float) -> bool:
    return abs(got - want) <= max(1.0, 0.02 * abs(want))


def check(folder: Path, prices_path: Path) -> list[tuple[bool, str]]:
    out = []
    onprem, cloud = av.load(folder / "onprem-avail.json"), av.load(folder / "cloud-avail.json")
    on_azs = {az for t in onprem.tiers for az in t.azs}
    cl_azs = {az for t in cloud.tiers for az in t.azs}
    out.append((len(on_azs) == 1, f"on-prem spec models one site (one fault domain label) — found {sorted(on_azs)}"))
    out.append((len(cl_azs) >= 2, f"cloud spec uses at least two AZs — found {sorted(cl_azs)}"))
    spof = av.single_points(cloud)
    out.append((not spof, "cloud spec has no single point of failure" + ("" if not spof else f" — {spof[0]}")))
    a_on, a_cl = av.analytic(onprem), av.analytic(cloud)
    out.append((a_cl > a_on, f"cloud availability is higher ({av.fmt_downtime(a_cl)} vs on-prem {av.fmt_downtime(a_on)})"))

    cmp = json.loads((folder / "comparison.json").read_text(encoding="utf-8"))
    for key, a in (("onprem_downtime_min_per_year", a_on), ("cloud_downtime_min_per_year", a_cl)):
        got = cmp.get(key)
        ok = isinstance(got, (int, float)) and close(got, downtime_min(a))
        out.append((ok, f"comparison.{key} = {got} matches availability.py ({downtime_min(a):.0f})"))

    prices = json.loads(prices_path.read_text(encoding="utf-8"))
    arch = json.loads((folder / "cloud-arch.json").read_text(encoding="utf-8"))
    envs = [r.get("env") for r in arch["resources"]]
    out.append((all(envs), "every cloud-arch resource has an env (tag)"))
    out.append((any(e and e != "prod" for e in envs), "cloud-arch includes non-prod (dev/ci) — it is part of the bill"))
    total = round(sum(ln.cost for ln in ce.lines_for(arch, prices)), 2)
    got = cmp.get("cloud_monthly")
    out.append((isinstance(got, (int, float)) and abs(got - total) <= 0.01 * total + 0.01,
                f"comparison.cloud_monthly = {got} matches cost_estimate.py ({total})"))
    onprem_monthly = cmp.get("onprem_monthly")
    out.append((isinstance(onprem_monthly, (int, float)) and onprem_monthly > 0, "comparison.onprem_monthly is a positive number"))
    assumptions = cmp.get("onprem_assumptions") or []
    out.append((len(assumptions) >= 4, f"at least 4 on-prem cost assumptions written down ({len(assumptions)})"))
    out.append((cmp.get("decision") in ("cloud", "onprem", "hybrid"), "comparison.decision is cloud, onprem or hybrid"))

    text = (folder / "decision.md").read_text(encoding="utf-8")
    for h in HEADINGS:
        out.append((h in text, f"decision.md has '{h}'"))
    if "EXAMPLE" in prices.get("_warning", "").upper():
        out.append(("example" in text.lower(), "decision.md says the prices are examples (not real)"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--prices", type=Path, required=True)
    a = ap.parse_args()
    try:
        results = check(a.folder, a.prices)
    except (OSError, KeyError, ValueError, TypeError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
