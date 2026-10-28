#!/usr/bin/env python3
"""Lab 05-C — ইচ্ছাকৃতভাবে খারাপ আচরণ করা TaskFlow-ধাঁচের API। শুধু 127.0.0.1-এ শোনে।

  python3 chaos_server.py --port 8098
  base URL-এর প্রথম অংশ mode বাছাই করে:
    http://127.0.0.1:8098/ok        → GET /ok/tasks: ৩টি task (১টি done)
    http://127.0.0.1:8098/flaky     → প্রথম ২ বার 503, তারপর ok
    http://127.0.0.1:8098/hang      → উত্তর দিতে ৬০ s
    http://127.0.0.1:8098/broken    → 200, কিন্তু অর্ধেক কাটা JSON
    http://127.0.0.1:8098/html502   → 502, body HTML (proxy-র error page-এর মতো)
  GET /reset → flaky-র গণনা শূন্য
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TASKS = {"items": [{"id": 1, "title": "a", "done": True}, {"id": 2, "title": "b", "done": False},
                   {"id": 3, "title": "c", "done": False}], "total": 3, "limit": 100, "offset": 0}


class Handler(BaseHTTPRequestHandler):
    flaky_calls = 0
    lock = threading.Lock()

    def log_message(self, fmt: str, *args: object) -> None:
        pass

    def reply(self, status: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:                                      # client আগেই চলে গেছে (timeout)
            pass

    def do_GET(self) -> None:  # noqa: N802
        mode = self.path.strip("/").split("/", 1)[0]
        ok = json.dumps(TASKS).encode()
        if self.path == "/reset":
            with Handler.lock:
                Handler.flaky_calls = 0
            return self.reply(200, b'{"reset": true}')
        if mode == "ok":
            return self.reply(200, ok)
        if mode == "flaky":
            with Handler.lock:
                Handler.flaky_calls += 1
                n = Handler.flaky_calls
            return self.reply(503, b'{"error": "unavailable"}') if n <= 2 else self.reply(200, ok)
        if mode == "hang":
            time.sleep(60)
            return self.reply(200, ok)
        if mode == "broken":
            return self.reply(200, ok[: len(ok) // 2])
        if mode == "html502":
            return self.reply(502, b"<html><body><h1>502 Bad Gateway</h1></body></html>", "text/html")
        return self.reply(404, b'{"error": "unknown mode"}')


def serve(port: int = 0) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    srv.daemon_threads = True                                # hang mode-এর thread-এর জন্য অপেক্ষা নয়
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> None:
    ap = argparse.ArgumentParser(description="Deliberately misbehaving API for Lab 05-C.")
    ap.add_argument("--port", type=int, default=8098)
    args = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    srv.daemon_threads = True
    print(f"chaos server on http://127.0.0.1:{args.port}  (modes: ok flaky hang broken html502; Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
