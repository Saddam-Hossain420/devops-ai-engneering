#!/usr/bin/env python3
"""alarm_defs.py — TaskFlow-এর জন্য চারটি অর্থবহ CloudWatch alarm-এর `put-metric-alarm` JSON বানায় (কিছু পাঠায় না)।

  python3 alarm_defs.py --lb-arn $LB --tg-arn $TG --instance $IID --topic-arn $TOPIC --out alarms/
  for f in alarms/*.json; do aws cloudwatch put-metric-alarm --cli-input-json file://$f; done

Alarm: ALB-এ target-এর 5xx · unhealthy target · EC2 status check ব্যর্থ · ALB-এর p95 response time।
User-এর অভিজ্ঞতা (5xx, latency) ও প্রতিকারযোগ্য কারণ (unhealthy, status check) — CPU% একা নয়।
ALB metric-এর dimension ARN থেকে বের হয়: LoadBalancer=app/NAME/ID, TargetGroup=targetgroup/NAME/ID।
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

LB_ARN = re.compile(r"^arn:aws[\w-]*:elasticloadbalancing:[\w-]+:\d{12}:loadbalancer/(app/[^/]+/[0-9a-f]+)$")
TG_ARN = re.compile(r"^arn:aws[\w-]*:elasticloadbalancing:[\w-]+:\d{12}:(targetgroup/[^/]+/[0-9a-f]+)$")


def lb_dimension(arn: str) -> str:
    m = LB_ARN.match(arn)
    if not m:
        raise ValueError(f"not an ALB ARN: {arn}")
    return m.group(1)


def tg_dimension(arn: str) -> str:
    m = TG_ARN.match(arn)
    if not m:
        raise ValueError(f"not a target group ARN: {arn}")
    return m.group(1)


def alarm(name: str, desc: str, ns: str, metric: str, dims: dict[str, str], stat: str, period: int, n: int, m: int,
          threshold: float, op: str, missing: str, topic: str, project: str) -> dict[str, Any]:
    d: dict[str, Any] = {
        "AlarmName": name, "AlarmDescription": desc, "ActionsEnabled": True,
        "AlarmActions": [topic], "OKActions": [topic],
        "Namespace": ns, "MetricName": metric, "Dimensions": [{"Name": k, "Value": v} for k, v in dims.items()],
        "Period": period, "EvaluationPeriods": n, "DatapointsToAlarm": m,
        "Threshold": threshold, "ComparisonOperator": op, "TreatMissingData": missing,
        "Tags": [{"Key": "Project", "Value": project}],
    }
    if stat.startswith("p"):
        d["ExtendedStatistic"] = stat
    else:
        d["Statistic"] = stat
    return d


def build(lb_arn: str, tg_arn: str, instance: str, topic: str, project: str, p95_ms: float) -> list[dict[str, Any]]:
    lb, tg = lb_dimension(lb_arn), tg_dimension(tg_arn)
    elb = "AWS/ApplicationELB"
    return [
        alarm(f"{project}-target-5xx", "TaskFlow returns 5xx — users see errors (runbook: L08-11 §12)", elb,
              "HTTPCode_Target_5XX_Count", {"LoadBalancer": lb, "TargetGroup": tg}, "Sum", 60, 5, 3, 5,
              "GreaterThanOrEqualToThreshold", "notBreaching", topic, project),       # traffic নেই = error নেই
        alarm(f"{project}-unhealthy-hosts", "At least one target failing health checks", elb, "UnHealthyHostCount",
              {"LoadBalancer": lb, "TargetGroup": tg}, "Maximum", 60, 3, 2, 1, "GreaterThanOrEqualToThreshold",
              "breaching", topic, project),                                          # metric নেই = সন্দেহজনক
        alarm(f"{project}-status-check", "EC2 instance or system status check failing", "AWS/EC2",
              "StatusCheckFailed", {"InstanceId": instance}, "Maximum", 60, 2, 2, 1,
              "GreaterThanOrEqualToThreshold", "breaching", topic, project),
        alarm(f"{project}-p95-latency", f"p95 response time above {p95_ms:g} ms", elb, "TargetResponseTime",
              {"LoadBalancer": lb, "TargetGroup": tg}, "p95", 60, 5, 3, p95_ms / 1000,
              "GreaterThanThreshold", "notBreaching", topic, project),                # metric সেকেন্ডে
    ]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Write put-metric-alarm JSON files for TaskFlow.")
    ap.add_argument("--lb-arn", required=True)
    ap.add_argument("--tg-arn", required=True)
    ap.add_argument("--instance", required=True)
    ap.add_argument("--topic-arn", required=True)
    ap.add_argument("--project", default="lab08")
    ap.add_argument("--p95-ms", type=float, default=500)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    try:
        alarms = build(a.lb_arn, a.tg_arn, a.instance, a.topic_arn, a.project, a.p95_ms)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    for d in alarms:
        path = a.out / f"{d['AlarmName']}.json"
        path.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        stat = d.get("Statistic") or d["ExtendedStatistic"]
        print(f"{path.name:<28} {d['MetricName']:<26} {stat:<7} {d['DatapointsToAlarm']}/{d['EvaluationPeriods']} "
              f"× {d['Period']}s  {d['ComparisonOperator']} {d['Threshold']:g}  missing={d['TreatMissingData']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
