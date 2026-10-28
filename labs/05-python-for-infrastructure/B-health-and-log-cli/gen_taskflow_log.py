#!/usr/bin/env python3
"""Lab 05-B — TaskFlow API-র (L05-13) format-এ কৃত্রিম JSON access log। Seed স্থির → একই output।

  python3 gen_taskflow_log.py --lines 5000 > taskflow-access.jsonl

প্রতিটি request লাইন: {"ts", "level", "msg": "request", "method", "path", "status", "duration_ms", "request_id", "client"}
সাথে কিছু অন্য লাইন ("listening", "stopped"), ও কয়েকটি ভাঙা লাইন (log rotation-এর মাঝে কাটা)।
`GET /tasks/{id}`-এ ইচ্ছাকৃতভাবে কিছু ধীর request ও 503 রাখা — report-এ যেন ধরা পড়ে।
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import UTC, datetime, timedelta

ROUTES = [("GET", "/tasks", 40), ("POST", "/tasks", 15), ("GET", "/tasks/{id}", 25),
          ("PATCH", "/tasks/{id}", 8), ("DELETE", "/tasks/{id}", 4), ("GET", "/health", 8)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    t = datetime(2026, 10, 27, 10, 0, tzinfo=UTC)
    out = [json.dumps({"ts": t.isoformat(), "level": "info", "msg": "listening", "url": "http://127.0.0.1:8000"})]
    for i in range(args.lines):
        t += timedelta(milliseconds=rng.randint(5, 400))
        method, route, _ = rng.choices(ROUTES, weights=[w for *_, w in ROUTES])[0]
        path = route.replace("{id}", str(rng.randint(1, 3000)))
        status = {"POST": 201, "DELETE": 204}.get(method, 200)
        duration = round(rng.lognormvariate(0.3, 0.5), 2)
        if rng.random() < 0.02:
            status = rng.choice([400, 404, 422])
        if route == "/tasks/{id}" and method == "GET" and rng.random() < 0.06:
            status, duration = 503, round(rng.uniform(800, 2500), 2)        # ধীর ও ব্যর্থ
        out.append(json.dumps({"ts": t.isoformat(timespec="milliseconds"), "level": "info", "msg": "request",
                               "method": method, "path": path, "status": status, "duration_ms": duration,
                               "request_id": f"r{i:06d}", "client": "127.0.0.1"}))
        if i in (args.lines // 3, 2 * args.lines // 3):
            out.append(out[-1][: len(out[-1]) // 2])                          # কাটা লাইন
    out.append(json.dumps({"ts": t.isoformat(), "level": "info", "msg": "stopped"}))
    sys.stdout.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
