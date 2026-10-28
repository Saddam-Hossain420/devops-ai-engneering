#!/usr/bin/env python3
"""ছোট L7 reverse proxy — round robin, passive health check, retry (শুধু idempotent), X-Forwarded-For,
X-Request-ID, 502/504। শুধু standard library; শেখার জন্য, production-এ Nginx/HAProxy/Envoy।

  python3 mini_proxy.py demo                                    # ৩টি local backend (একটি বন্ধ) + proxy
  python3 mini_proxy.py serve --port 8080 --backend 127.0.0.1:8001 --backend 127.0.0.1:8002
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

IDEMPOTENT = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
              "proxy-authorization", "proxy-authenticate"}


class Pool:
    """Backend তালিকা; ব্যর্থ backend কিছুক্ষণের জন্য বাদ (passive health check / outlier ejection)।"""

    def __init__(self, backends: list[str], eject_seconds: float = 10.0) -> None:
        self.backends = backends
        self.eject_seconds = eject_seconds
        self.down_until: dict[str, float] = {}
        self.next = 0
        self.lock = threading.Lock()

    def candidates(self) -> list[str]:
        """শুধু সুস্থ backend-দের মধ্যে round robin; বাদ পড়াগুলো একেবারে শেষে (সবাই ব্যর্থ হলে শেষ চেষ্টা)।
        বাদ পড়া backend-কে rotation-এ রেখে skip করলে তার ভাগ পাশের backend পায় — অসম load।"""
        with self.lock:
            now = time.monotonic()
            healthy = [b for b in self.backends if self.down_until.get(b, 0) <= now]
            down = [b for b in self.backends if b not in healthy]
            if healthy:
                i = self.next % len(healthy)
                healthy = healthy[i:] + healthy[:i]
            self.next += 1
            return healthy + down

    def mark_down(self, backend: str) -> None:
        with self.lock:
            self.down_until[backend] = time.monotonic() + self.eject_seconds


def make_handler(pool: Pool, timeout: float):
    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def _proxy(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            rid = self.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP}
            prior = self.headers.get("X-Forwarded-For")
            client = self.client_address[0]
            headers["X-Forwarded-For"] = f"{prior}, {client}" if prior else client
            headers["X-Forwarded-Proto"] = "http"
            headers["X-Request-ID"] = rid
            tries = pool.candidates() if self.command in IDEMPOTENT else pool.candidates()[:1]
            for backend in tries:
                host, port = backend.rsplit(":", 1)
                conn = http.client.HTTPConnection(host, int(port), timeout=timeout)
                try:
                    conn.request(self.command, self.path, body=body, headers=headers)
                    resp = conn.getresponse()
                    data = resp.read()
                except (TimeoutError, socket.timeout):
                    conn.close()
                    # timeout-এ retry নয়: backend হয়তো কাজটা করছে; আবার পাঠালে দ্বিগুণ load
                    return self._error(504, "backend timeout", rid, backend)
                except OSError:
                    conn.close()
                    pool.mark_down(backend)
                    continue  # connection-ই হয়নি → অন্য backend-এ চেষ্টা নিরাপদ
                conn.close()
                self.send_response(resp.status, resp.reason)
                for k, v in resp.getheaders():
                    if k.lower() not in HOP_BY_HOP and k.lower() != "content-length":
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Upstream", backend)
                self.send_header("X-Request-ID", rid)
                self.end_headers()
                self.wfile.write(data)
                return
            self._error(502, "no backend reachable", rid, ",".join(tries))

        def _error(self, code: int, msg: str, rid: str, backend: str) -> None:
            body = json.dumps({"error": msg, "request_id": rid}).encode() + b"\n"
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Upstream", backend)
            self.send_header("X-Request-ID", rid)
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _proxy

    return ProxyHandler


def start_proxy(backends: list[str], port: int = 0, timeout: float = 5.0,
                eject_seconds: float = 10.0) -> tuple[ThreadingHTTPServer, int]:
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Pool(backends, eject_seconds), timeout))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def start_backend(name: str, delay: float = 0.0) -> tuple[ThreadingHTTPServer, int]:
    """Demo backend: নিজের নাম ও proxy যে header যোগ করেছে তা JSON-এ ফেরত দেয়।"""

    class Backend(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            time.sleep(delay)
            body = json.dumps({"backend": name, "path": self.path,
                               "x_forwarded_for": self.headers.get("X-Forwarded-For"),
                               "x_request_id": self.headers.get("X-Request-ID")}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def stop(srv: ThreadingHTTPServer) -> None:
    srv.shutdown()
    srv.server_close()


def dead_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def get(port: int, path: str = "/") -> tuple[int, dict[str, str], bytes]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        return r.status, dict(r.getheaders()), r.read()
    finally:
        conn.close()


def demo() -> int:
    b1, p1 = start_backend("app-1")
    b2, p2 = start_backend("app-2")
    dead = dead_port()
    backends = [f"127.0.0.1:{p1}", f"127.0.0.1:{dead}", f"127.0.0.1:{p2}"]
    proxy, pport = start_proxy(backends)
    print(f"proxy :{pport} -> app-1 :{p1}, (dead) :{dead}, app-2 :{p2}")
    try:
        for i in range(6):
            t0 = time.perf_counter()
            status, hdrs, body = get(pport, f"/item/{i}")
            ms = (time.perf_counter() - t0) * 1000
            info = json.loads(body)
            print(f"GET /item/{i} -> {status} from {info['backend']}  ({ms:5.1f} ms)  "
                  f"XFF={info['x_forwarded_for']}  request-id={hdrs['X-Request-ID']}")
    finally:
        stop(proxy)
        stop(b1)
        stop(b2)
    proxy, pport = start_proxy([f"127.0.0.1:{dead}"])
    try:
        status, _, body = get(pport)
        print(f"all backends dead -> {status} {body.decode().strip()}")
    finally:
        stop(proxy)
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tiny L7 reverse proxy (learning tool).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8080)
    s.add_argument("--backend", action="append", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        return demo()
    srv, port = start_proxy(args.backend, args.port)
    print(f"proxy on 127.0.0.1:{port} -> {', '.join(args.backend)} (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop(srv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
