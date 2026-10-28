#!/usr/bin/env python3
"""keepalive_bench.py — upstream keepalive কেন: TaskFlow-এ প্রতি request-এ নতুন TCP connection বনাম একটি connection reuse।

  python3 keepalive_bench.py --requests 1000

nginx-এর `upstream { keepalive N; }` + `proxy_http_version 1.1; proxy_set_header Connection "";` ঠিক এই পার্থক্য তৈরি করে।
TaskFlow (L05-13) একই process-এ 127.0.0.1-এর একটি OS-নির্বাচিত port-এ চলে; temp database।
"""
from __future__ import annotations

import argparse
import http.client
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "05-python-for-infrastructure" / "code" / "L05-13"))
import taskflow_api as tf  # noqa: E402


def bench(port: int, n: int, reuse: bool) -> float:
    start = time.perf_counter()
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10) if reuse else None
    for _ in range(n):
        c = conn or http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        c.request("GET", "/health")
        resp = c.getresponse()
        resp.read()
        if resp.status != 200:
            raise RuntimeError(f"unexpected status {resp.status}")
        if not reuse:
            c.close()
    if conn:
        conn.close()
    return time.perf_counter() - start


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--requests", type=int, default=1000)
    a = ap.parse_args()
    tf.log.disabled = True
    with tempfile.TemporaryDirectory() as d:
        srv = tf.make_server(tf.Config(port=0, db_path=str(Path(d, "bench.db"))))
        threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        port = srv.server_address[1]
        bench(port, 50, True)                                     # warm-up
        for label, reuse in (("new connection per request", False), ("one keep-alive connection", True)):
            took = bench(port, a.requests, reuse)
            print(f"{label:<28} {a.requests} requests in {took:6.2f} s  → {a.requests / took:7.0f} req/s, "
                  f"{took / a.requests * 1000:5.2f} ms each")
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    main()
