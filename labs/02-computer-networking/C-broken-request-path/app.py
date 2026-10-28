#!/usr/bin/env python3
"""Lab 02-C app: GET /health → {"status": "ok"}। Bind address ও port environment থেকে (LAB_BIND, LAB_PORT)।"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Health(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        code, body = (200, {"status": "ok"}) if self.path == "/health" else (404, {"error": "not found"})
        data = json.dumps(body).encode() + b"\n"
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    bind = os.environ.get("LAB_BIND", "127.0.0.1")
    port = int(os.environ.get("LAB_PORT", "8080"))
    print(f"lab02c app listening on {bind}:{port}", flush=True)
    ThreadingHTTPServer((bind, port), Health).serve_forever()
