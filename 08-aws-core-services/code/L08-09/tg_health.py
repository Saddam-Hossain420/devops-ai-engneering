#!/usr/bin/env python3
"""tg_health.py — ALB target group-এর health ব্যাখ্যা ও health-check setting-এর হিসাব (offline)।

  aws elbv2 describe-target-groups --names lab08-app > tg.json
  aws elbv2 describe-target-group-attributes --target-group-arn $TG > tg-attrs.json
  aws elbv2 describe-target-health --target-group-arn $TG > health.json
  python3 tg_health.py tg.json --attributes tg-attrs.json --health health.json --app-shutdown 10

Reason code-এর অর্থ AWS ELB documentation অনুযায়ী; পরবর্তী ধাপ এই course-এর tool-এর দিকে নির্দেশ করে।
হিসাব: unhealthy ধরতে ≈ interval × UnhealthyThresholdCount; ফিরতে ≈ interval × HealthyThresholdCount।
Exit: 0 সব target healthy ও setting ঠিক, 1 অন্যথায়, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REASONS = {
    "Elb.RegistrationInProgress": "target is being registered — wait",
    "Elb.InitialHealthChecking": "first health checks running — wait HealthyThresholdCount × interval",
    "Target.ResponseCodeMismatch": "app answered, but not with the matcher code — wrong path, redirect (301/302), or auth; "
                                   "curl the health path from inside the VPC",
    "Target.Timeout": "no answer within HealthCheckTimeout — packets dropped by a security group/NACL (sg_reach.py), "
                      "or the app is too slow",
    "Target.FailedHealthChecks": "connection failed — app down, wrong port, or listening only on 127.0.0.1 "
                                 "(refused; ss -ltnp on the instance)",
    "Target.NotRegistered": "target is not registered in this group",
    "Target.NotInUse": "target group not used by any listener rule, or target's AZ not enabled on the load balancer",
    "Target.DeregistrationInProgress": "draining — in-flight requests finish up to the deregistration delay",
    "Target.InvalidState": "instance is stopped or terminated",
    "Target.IpUnusable": "IP is in use by a load balancer or invalid",
    "Target.HealthCheckDisabled": "health checks are disabled",
    "Elb.InternalError": "ELB internal error — retry, check AWS Health",
}


def attrs_of(doc: dict[str, Any] | None) -> dict[str, str]:
    return {a["Key"]: a["Value"] for a in (doc or {}).get("Attributes", [])}


def check_settings(tg: dict[str, Any], attrs: dict[str, str], app_shutdown: float | None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    interval, timeout = tg["HealthCheckIntervalSeconds"], tg["HealthCheckTimeoutSeconds"]
    down, up = interval * tg["UnhealthyThresholdCount"], interval * tg["HealthyThresholdCount"]
    out.append(("INFO", f"detect a dead target in ≈{down}s, readmit a recovered one in ≈{up}s"))
    if timeout >= interval:
        out.append(("WARN", f"HealthCheckTimeout {timeout}s ≥ interval {interval}s — checks overlap"))
    if down > 60:
        out.append(("WARN", f"{down}s to detect a dead target — users get errors that long; lower interval or threshold"))
    path = tg.get("HealthCheckPath", "/")
    if tg.get("HealthCheckProtocol", "HTTP").startswith("HTTP") and path in ("/", ""):
        out.append(("WARN", "health check on '/' — use a cheap dedicated endpoint (/health) that does not need a login"))
    delay = attrs.get("deregistration_delay.timeout_seconds")
    if delay is not None and app_shutdown is not None and float(delay) < app_shutdown:
        out.append(("WARN", f"deregistration delay {delay}s < app shutdown {app_shutdown}s — requests are cut off "
                            "during deploys"))
    elif delay is not None and float(delay) >= 300:
        out.append(("INFO", f"deregistration delay {delay}s (default) — deploys wait that long; lower it if requests "
                            "are short"))
    return out


def explain(health: dict[str, Any]) -> list[tuple[str, str]]:
    out = []
    for d in health.get("TargetHealthDescriptions", []):
        t, h = d["Target"], d["TargetHealth"]
        name = f"{t['Id']}:{t.get('Port', '?')}"
        if h["State"] == "healthy":
            out.append(("OK", f"{name} healthy"))
            continue
        reason = h.get("Reason", "?")
        out.append(("WARN" if h["State"] in ("initial", "draining") else "ERROR",
                    f"{name} {h['State']} — {reason}: {REASONS.get(reason, h.get('Description', 'see AWS docs'))}"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Explain ALB target health and health-check settings (offline).")
    ap.add_argument("target_groups", type=Path)
    ap.add_argument("--attributes", type=Path)
    ap.add_argument("--health", type=Path)
    ap.add_argument("--app-shutdown", type=float, help="seconds your app needs to finish in-flight requests")
    a = ap.parse_args(argv)
    try:
        tgs = json.loads(a.target_groups.read_text(encoding="utf-8"))["TargetGroups"]
        attrs = attrs_of(json.loads(a.attributes.read_text(encoding="utf-8")) if a.attributes else None)
        health = json.loads(a.health.read_text(encoding="utf-8")) if a.health else {}
        bad = 0
        for tg in tgs:
            print(f"{tg['TargetGroupName']} ({tg['Protocol']}:{tg['Port']}, check "
                  f"{tg.get('HealthCheckProtocol')} {tg.get('HealthCheckPath', '')} expect {tg.get('Matcher', {}).get('HttpCode', '?')})")
            for lvl, msg in check_settings(tg, attrs, a.app_shutdown) + explain(health):
                print(f"  {lvl:<5}  {msg}")
                bad += lvl in ("WARN", "ERROR")
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
