#!/usr/bin/env python3
"""Lab 07-C verification — আপনার fixed-policy.json ও risk-analysis.md যাচাই (offline, কোনো cloud call নেই)।

  python3 check_c.py ~/lab07c/fixed-policy.json --analysis ~/lab07c/risk-analysis.md
  python3 check_c.py broken-policy.json              # দেখুন ভাঙা policy কোথায় কোথায় FAIL করে

যাচাই: L07-05-এর policy_eval দিয়ে required.json-এর প্রতিটি request allow ও dangerous.json-এর প্রতিটি deny;
policy_lint-এ কোনো CRITICAL নেই; analysis-এ ভাঙা policy-র প্রতিটি Sid-এর আলোচনা।
সীমা: সরল evaluator (SCP/permission boundary/resource policy নেই) — আসল account-এ IAM policy simulator-এ মেলান।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "07-cloud-fundamentals" / "code" / "L07-05"))
import policy_eval as pe  # noqa: E402
import policy_lint as pl  # noqa: E402


def check(policy: dict, analysis: str | None) -> list[tuple[bool, str]]:
    out = []
    for name, want in (("required.json", True), ("dangerous.json", False)):
        for r in json.loads((HERE / name).read_text(encoding="utf-8")):
            d = pe.evaluate([policy], r["action"], r["resource"], r.get("context"))
            verb = "allowed" if want else "denied"
            out.append((d.allowed == want, f"{verb}: {r['action']} — {r['why']} [{d.reason}]"))
    findings = pl.lint_policy(policy, "policy")
    crit = [msg for level, _, msg in findings if level == 2]
    warn = [msg for level, _, msg in findings if level == 1]
    out.append((not crit, "policy_lint: no CRITICAL" + ("" if not crit else f" — {crit[0]}")))
    out.append((len(warn) <= 1, f"policy_lint: at most 1 WARN ({len(warn)})" + ("" if len(warn) <= 1 else f" — {warn[0]}")))
    if analysis is not None:
        broken = json.loads((HERE / "broken-policy.json").read_text(encoding="utf-8"))
        for s in broken["Statement"]:
            out.append((s["Sid"] in analysis, f"risk-analysis.md discusses {s['Sid']}"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("policy", type=Path)
    ap.add_argument("--analysis", type=Path)
    a = ap.parse_args()
    try:
        policy = json.loads(a.policy.read_text(encoding="utf-8"))
        analysis = a.analysis.read_text(encoding="utf-8") if a.analysis else None
        results = check(policy, analysis)
    except (OSError, json.JSONDecodeError, ValueError, AttributeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    if a.analysis is None:
        print("note: --analysis not given — risk-analysis.md not checked")
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed and a.analysis is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
