#!/usr/bin/env python3
"""Latency experiment — hypothesis যাচাইয়ের জন্য নিয়ন্ত্রিত measurement.

Script নিজেই 127.0.0.1-এ একটি ছোট HTTP server চালায় (শুধু এই machine থেকে access),
তারপর দুটি endpoint-এ অনেকবার request পাঠিয়ে latency-র বণ্টন মাপে।

Endpoint:
  /work?ms=N     — N millisecond অপেক্ষা করে উত্তর দেয় (কৃত্রিম কাজ)
  /flaky?ms=N&fail=P — P% সম্ভাবনায় HTTP 500 দেয়

Usage:
  python3 latency_experiment.py --baseline-ms 5 --variant-ms 25 --requests 200
  python3 latency_experiment.py --variant-ms 5 --fail-percent 10
"""
from __future__ import annotations

import argparse
import http.client
import math
import random
import statistics
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class Handler(BaseHTTPRequestHandler):
    rng = random.Random(42)  # seed: experiment পুনরাবৃত্তিযোগ্য রাখতে
    lock = threading.Lock()

    def do_GET(self) -> None:  # noqa: N802 (http.server naming)
        url = urlparse(self.path)
        q = parse_qs(url.query)
        ms = float(q.get("ms", ["0"])[0])
        fail = float(q.get("fail", ["0"])[0])
        if url.path not in ("/work", "/flaky"):
            self.send_error(404)
            return
        time.sleep(ms / 1000)
        with self.lock:
            failed = url.path == "/flaky" and self.rng.random() * 100 < fail
        body = b"error\n" if failed else b"ok\n"
        self.send_response(500 if failed else 200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # প্রতিটি request terminal-এ না ছাপাতে
        pass


@dataclass(frozen=True)
class Result:
    latencies_ms: list[float]
    errors: int

    @property
    def total(self) -> int:
        return len(self.latencies_ms)


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile (L00-03-এর মত)."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    return ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1]


def summarize(result: Result) -> dict[str, float]:
    v = result.latencies_ms
    return {
        "requests": result.total,
        "error_rate_percent": round(100 * result.errors / result.total, 1),
        "min": round(min(v), 1),
        "p50": round(percentile(v, 50), 1),
        "p95": round(percentile(v, 95), 1),
        "p99": round(percentile(v, 99), 1),
        "max": round(max(v), 1),
        "mean": round(statistics.mean(v), 1),
        "stdev": round(statistics.stdev(v), 1) if len(v) > 1 else 0.0,
    }


def run(port: int, path: str, n: int, warmup: int = 5) -> Result:
    """একই connection-এ n বার request; প্রথম warmup বার মাপা হয় না।"""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    latencies: list[float] = []
    errors = 0
    try:
        for i in range(warmup + n):
            start = time.perf_counter()  # perf_counter: সময় মাপার জন্য সবচেয়ে সূক্ষ্ম monotonic clock
            conn.request("GET", path)
            resp = conn.getresponse()
            resp.read()
            elapsed = (time.perf_counter() - start) * 1000
            if i < warmup:
                continue
            latencies.append(elapsed)
            if resp.status >= 500:
                errors += 1
    finally:
        conn.close()
    return Result(latencies, errors)


def start_server() -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)  # port 0 = OS একটি খালি port দেয়
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def stop_server(server: ThreadingHTTPServer) -> None:
    server.shutdown()      # serve_forever loop থামায়
    server.server_close()  # listening socket বন্ধ করে (না করলে socket leak)


def print_table(rows: dict[str, dict[str, float]]) -> None:
    keys = ["requests", "error_rate_percent", "min", "p50", "p95", "p99", "max", "mean", "stdev"]
    print(f"{'metric (ms)':20}" + "".join(f"{name:>14}" for name in rows))
    for k in keys:
        print(f"{k:20}" + "".join(f"{rows[name][k]:>14}" for name in rows))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Controlled latency experiment against a local server.")
    p.add_argument("--baseline-ms", type=float, default=5)
    p.add_argument("--variant-ms", type=float, default=25)
    p.add_argument("--fail-percent", type=float, default=0, help="variant-এ ব্যর্থতার হার")
    p.add_argument("--requests", type=int, default=200)
    args = p.parse_args(argv)
    if args.requests < 2:
        p.error("--requests must be at least 2")

    server, port = start_server()
    try:
        base = run(port, f"/work?ms={args.baseline_ms}", args.requests)
        var = run(port, f"/flaky?ms={args.variant_ms}&fail={args.fail_percent}", args.requests)
    finally:
        stop_server(server)

    rows = {"baseline": summarize(base), "variant": summarize(var)}
    print(f"server 127.0.0.1:{port} — baseline {args.baseline_ms}ms, variant {args.variant_ms}ms, "
          f"variant fail {args.fail_percent}%\n")
    print_table(rows)
    diff = rows["variant"]["p50"] - rows["baseline"]["p50"]
    print(f"\np50 difference: {diff:+.1f} ms (expected about {args.variant_ms - args.baseline_ms:+.1f} ms)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
