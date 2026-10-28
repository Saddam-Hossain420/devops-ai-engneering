#!/usr/bin/env python3
"""flaky_server.py — অনুশীলনের জন্য local HTTP server যা ইচ্ছাকৃতভাবে ভুল আচরণ করে। শুধু 127.0.0.1-এ শোনে।

  python3 flaky_server.py --port 8099
  /health      → 200
  /flaky       → প্রথম ২ বার 503, তারপর 200 (প্রতিটি client-এর জন্য নয় — server-জুড়ে গণনা)
  /ratelimit   → প্রথমবার 429 + Retry-After: 1, তারপর 200
  /slow?s=3    → s সেকেন্ড পরে 200
  /notfound    → 404
  /reset       → গণনা শূন্য
  POST /orders → প্রতিবার নতুন order (idempotency key একই হলে আগের order ফেরত)
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class State:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.flaky = 0
        self.ratelimit = 0
        self.orders: list[dict[str, object]] = []
        self.by_key: dict[str, dict[str, object]] = {}


class Handler(BaseHTTPRequestHandler):
    state = State()
    flaky_failures = 2

    def log_message(self, fmt: str, *args: object) -> None:      # test-এর output পরিষ্কার রাখা
        pass

    def send_json(self, status: int, payload: object, headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        st = self.state
        if url.path == "/health":
            self.send_json(200, {"status": "ok"})
        elif url.path == "/flaky":
            with st.lock:
                st.flaky += 1
                n = st.flaky
            if n <= self.flaky_failures:
                self.send_json(503, {"error": "temporarily unavailable", "call": n})
            else:
                self.send_json(200, {"status": "ok", "call": n})
        elif url.path == "/ratelimit":
            with st.lock:
                st.ratelimit += 1
                n = st.ratelimit
            if n == 1:
                self.send_json(429, {"error": "slow down"}, {"Retry-After": "1"})
            else:
                self.send_json(200, {"status": "ok", "call": n})
        elif url.path == "/slow":
            time.sleep(float(parse_qs(url.query).get("s", ["3"])[0]))
            self.send_json(200, {"status": "finally"})
        elif url.path == "/reset":
            with st.lock:
                st.reset()
            self.send_json(200, {"reset": True})
        else:
            self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/orders":
            self.send_json(404, {"error": "not found"})
            return
        key = self.headers.get("Idempotency-Key")
        with self.state.lock:
            if key and key in self.state.by_key:
                order = self.state.by_key[key]
            else:
                order = {"id": len(self.state.orders) + 1}
                self.state.orders.append(order)
                if key:
                    self.state.by_key[key] = order
        self.send_json(201, order)


def serve(port: int = 0) -> ThreadingHTTPServer:
    """Background thread-এ server চালু; port=0 হলে OS একটি খালি port দেয় (test-এর জন্য)।"""
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main() -> None:
    ap = argparse.ArgumentParser(description="Deliberately unreliable local HTTP server.")
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"listening on http://127.0.0.1:{args.port} (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
