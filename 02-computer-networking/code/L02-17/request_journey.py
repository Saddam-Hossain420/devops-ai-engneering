#!/usr/bin/env python3
"""একটি request-এর পূর্ণ যাত্রা, loopback-এ: client → DNS → TCP → edge proxy (L7) → app → SQLite database।
প্রতিটি hop একই X-Request-ID দিয়ে structured (JSON) log লেখে; শেষে request-প্রতি timeline।

  python3 request_journey.py                     # স্বাভাবিক — ৩টি request
  python3 request_journey.py --fault db-slow     # database ধীর → proxy timeout → 504
  python3 request_journey.py --fault app-down    # app বন্ধ → 502
  python3 request_journey.py --fault db-error    # query ব্যর্থ → app 500

শুধু standard library; database একটি temporary SQLite file; সব শেষে মুছে যায়।
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONNECT_TIMEOUT = 3.0   # backend-এ TCP connect-এর সীমা (Nginx: proxy_connect_timeout)
READ_TIMEOUT = 1.0      # connect-এর পরে উত্তরের অপেক্ষা (Nginx: proxy_read_timeout)


class Log:
    """সব hop-এর structured log এক জায়গায় (বাস্তবে: প্রতিটি service নিজের log → central log system)।"""

    def __init__(self) -> None:
        self.lines: list[dict] = []
        self.lock = threading.Lock()

    def write(self, **fields: object) -> None:
        with self.lock:
            self.lines.append({"ts": round(time.time(), 4), **fields})

    def for_request(self, rid: str) -> list[dict]:
        with self.lock:
            return [l for l in self.lines if l.get("rid") == rid]


def make_db(path: Path) -> None:
    db = sqlite3.connect(path)
    try:
        with db:  # sqlite3-এর `with` শুধু commit/rollback করে, connection বন্ধ করে না — তাই আলাদা close()
            db.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            db.executemany("INSERT INTO items VALUES (?, ?)", [(1, "gpu-a100"), (2, "gpu-l4"), (3, "cpu-c7")])
    finally:
        db.close()


def app_handler(db_path: Path, log: Log, fault: str | None):
    class App(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def _reply(self, code: int, body: dict, rid: str) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Request-ID", rid)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            t0 = time.perf_counter()
            rid = self.headers.get("X-Request-ID", "-")
            item_id = self.path.rstrip("/").rsplit("/", 1)[-1]
            conn = sqlite3.connect(db_path)
            conn.create_function("pause", 1, lambda s: time.sleep(s) or 0)
            q0 = time.perf_counter()
            try:
                table = "missing_table" if fault == "db-error" else "items"
                delay = 1.5 if fault == "db-slow" else 0.0
                # parameterized query — কখনো string-এ user input জোড়া নয় (SQL injection)
                row = conn.execute(f"SELECT name, pause(?) FROM {table} WHERE id = ?", (delay, item_id)).fetchone()
                db_ms = (time.perf_counter() - q0) * 1000
                log.write(hop="db", rid=rid, query=f"SELECT ... FROM {table}", ms=round(db_ms, 1), ok=True)
                code, body = (200, {"id": int(item_id), "name": row[0]}) if row else (404, {"error": "not found"})
            except sqlite3.Error as exc:
                db_ms = (time.perf_counter() - q0) * 1000
                log.write(hop="db", rid=rid, ms=round(db_ms, 1), ok=False, error=str(exc))
                code, body = 500, {"error": "database error", "request_id": rid}  # internal detail client-এ নয়
            finally:
                conn.close()
            try:
                self._reply(code, body, rid)
                sent = True
            except OSError:              # proxy আগেই ছেড়ে চলে গেছে (timeout)
                sent = False
                self.close_connection = True  # keep-alive loop যেন মৃত connection-এ আর না পড়ে
            log.write(hop="app", rid=rid, path=self.path, status=code,
                      ms=round((time.perf_counter() - t0) * 1000, 1), db_ms=round(db_ms, 1), response_delivered=sent)

    return App


def proxy_handler(upstream: tuple[str, int], log: Log):
    class Proxy(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: object) -> None:
            pass

        def do_GET(self) -> None:
            t0 = time.perf_counter()
            rid = self.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
            conn = http.client.HTTPConnection(*upstream)
            try:
                try:
                    conn.sock = socket.create_connection(upstream, timeout=CONNECT_TIMEOUT)
                except OSError:
                    raise ConnectionError("connect failed") from None
                conn.sock.settimeout(READ_TIMEOUT)
                conn.request("GET", self.path, headers={"X-Request-ID": rid,
                                                        "X-Forwarded-For": self.client_address[0]})
                resp = conn.getresponse()
                status, body = resp.status, resp.read()
            except ConnectionError:
                status, body = 502, json.dumps({"error": "upstream unreachable", "request_id": rid}).encode()
            except (TimeoutError, socket.timeout):
                status, body = 504, json.dumps({"error": "upstream timeout", "request_id": rid}).encode()
            except OSError:
                status, body = 502, json.dumps({"error": "upstream unreachable", "request_id": rid}).encode()
            finally:
                conn.close()
            ms = (time.perf_counter() - t0) * 1000
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-ID", rid)
            self.end_headers()
            self.wfile.write(body)
            log.write(hop="proxy", rid=rid, path=self.path, status=status, upstream_ms=round(ms, 1))

    return Proxy


def serve(handler) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def client_request(host: str, port: int, path: str, log: Log) -> tuple[int, str, dict]:
    """Browser-এর কাজ: DNS, TCP connect, request, প্রথম byte পর্যন্ত সময় — আলাদা করে মাপা।"""
    t0 = time.perf_counter()
    addr = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
    t_dns = time.perf_counter()
    sock = socket.create_connection(addr, timeout=10)
    t_tcp = time.perf_counter()
    conn = http.client.HTTPConnection(host, port)
    conn.sock = sock
    try:
        conn.request("GET", path)
        resp = conn.getresponse()
        t_first = time.perf_counter()
        resp.read()
        status, rid = resp.status, resp.getheader("X-Request-ID", "-")
    finally:
        conn.close()
    timing = {"dns_ms": round((t_dns - t0) * 1000, 1), "connect_ms": round((t_tcp - t_dns) * 1000, 1),
              "ttfb_ms": round((t_first - t_tcp) * 1000, 1), "total_ms": round((time.perf_counter() - t0) * 1000, 1)}
    log.write(hop="client", rid=rid, path=path, status=status, **timing)
    return status, rid, timing


class Stack:
    """তিনটি component চালু করে; `with` শেষে সব বন্ধ ও temp database মোছা।"""

    def __init__(self, fault: str | None = None) -> None:
        self.fault, self.log = fault, Log()

    def __enter__(self) -> "Stack":
        self.tmp = tempfile.TemporaryDirectory(prefix="journey-")
        db = Path(self.tmp.name) / "app.db"
        make_db(db)
        self.app = serve(app_handler(db, self.log, self.fault))
        app_addr = self.app.server_address[:2]
        if self.fault == "app-down":
            self.app.shutdown()
            self.app.server_close()
        self.proxy = serve(proxy_handler(app_addr, self.log))
        self.port = self.proxy.server_address[1]
        return self

    def __exit__(self, *exc: object) -> None:
        self.proxy.shutdown()
        self.proxy.server_close()
        if self.fault != "app-down":
            self.app.shutdown()
            self.app.server_close()
        self.tmp.cleanup()

    def request(self, path: str) -> tuple[int, str, dict]:
        return client_request("localhost", self.port, path, self.log)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Trace one request through client, proxy, app and database.")
    ap.add_argument("--fault", choices=["db-slow", "app-down", "db-error"])
    args = ap.parse_args(argv)
    with Stack(args.fault) as st:
        paths = ["/items/1"] if args.fault else ["/items/1", "/items/2", "/items/99"]
        for path in paths:
            status, rid, t = st.request(path)
            if args.fault == "db-slow":
                time.sleep(0.8)          # app-এর কাজ শেষ হওয়া পর্যন্ত অপেক্ষা — log দেখাতে
            print(f"GET {path} → {status}  request-id {rid}")
            print(f"  client: dns {t['dns_ms']} ms | tcp connect {t['connect_ms']} ms | "
                  f"time to first byte {t['ttfb_ms']} ms | total {t['total_ms']} ms")
            for line in st.log.for_request(rid):
                if line["hop"] != "client":
                    shown = {k: v for k, v in line.items() if k not in ("ts", "rid")}
                    print(f"  {json.dumps(shown, ensure_ascii=False)}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
