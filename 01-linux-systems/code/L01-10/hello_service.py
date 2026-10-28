#!/usr/bin/env python3
"""ছোট HTTP service — systemd দিয়ে চালানোর অনুশীলনের জন্য (শুধু standard library)।

- GET /health → 200 "ok"
- GET /       → greeting (GREETING env var থেকে)
- log stdout-এ (systemd journald-এ ধরে) — নিজে log file লেখে না
- SIGTERM-এ graceful shutdown (L01-08)

Usage:
  python3 hello_service.py --port 8080
  GREETING="hi from systemd" python3 hello_service.py
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("hello")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body, code = b"ok\n", 200
        elif self.path == "/":
            body, code = (os.environ.get("GREETING", "hello") + "\n").encode(), 200
        else:
            body, code = b"not found\n", 404
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s %s", self.address_string(), fmt % args)


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Tiny HTTP service for systemd practice.")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    args = p.parse_args(argv)
    # timestamp নেই: journald নিজেই প্রতিটি লাইনে সময় যোগ করে
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s", stream=sys.stdout)

    server = build_server(args.host, args.port)

    def stop(signum: int, _frame) -> None:
        log.info("received %s, shutting down", signal.Signals(signum).name)
        # shutdown() serve_forever শেষ হওয়া পর্যন্ত অপেক্ষা করে — তাই আলাদা thread থেকে ডাকা
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log.info("listening on %s:%d (pid %d)", args.host, args.port, os.getpid())
    try:
        server.serve_forever()
    finally:
        server.server_close()
    log.info("stopped cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
