#!/usr/bin/env python3
"""HTTP/1.1 নিজের হাতে — socket-এ raw request পাঠানো ও response parse, শুধু standard library।

Commands:
  python3 http_raw.py demo                         # loopback-এ local server চালিয়ে raw exchange দেখায় (network লাগে না)
  python3 http_raw.py get http://127.0.0.1:8000/   # যেকোনো plain-HTTP URL (HTTPS নয় — সেটা L02-08)
  python3 http_raw.py get http://example.com/ --show-raw

শেখার tool; production-এ curl, requests/httpx ব্যবহার করুন।
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

CRLF = b"\r\n"


def build_request(method: str, host: str, path: str = "/", headers: dict[str, str] | None = None,
                  body: bytes = b"", keep_alive: bool = True) -> bytes:
    """Request line + headers + খালি লাইন + body. HTTP/1.1-এ Host header বাধ্যতামূলক।"""
    lines = [f"{method} {path} HTTP/1.1", f"Host: {host}", "User-Agent: http_raw/1.0"]
    if not keep_alive:
        lines.append("Connection: close")
    for k, v in (headers or {}).items():
        lines.append(f"{k}: {v}")
    if body:
        lines.append(f"Content-Length: {len(body)}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


@dataclass
class Response:
    version: str
    status: int
    reason: str
    headers: list[tuple[str, str]] = field(default_factory=list)
    body: bytes = b""

    def header(self, name: str) -> str | None:
        """Header নাম case-insensitive (RFC 9110)।"""
        for k, v in self.headers:
            if k.lower() == name.lower():
                return v
        return None


def parse_head(head: bytes) -> Response:
    lines = head.decode("latin-1").split("\r\n")
    parts = lines[0].split(" ", 2)
    if len(parts) < 2 or not parts[0].startswith("HTTP/"):
        raise ValueError(f"bad status line: {lines[0]!r}")
    headers = []
    for line in lines[1:]:
        if not line:
            continue
        name, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"bad header line: {line!r}")
        headers.append((name.strip(), value.strip()))
    return Response(parts[0], int(parts[1]), parts[2] if len(parts) > 2 else "", headers)


def decode_chunked(data: bytes) -> tuple[bytes, int]:
    """Chunked body decode: '<hex size>\\r\\n<data>\\r\\n' ... '0\\r\\n\\r\\n'. (body, ব্যবহৃত byte)।
    অসম্পূর্ণ data হলে ValueError('incomplete')."""
    out, i = b"", 0
    while True:
        end = data.find(CRLF, i)
        if end < 0:
            raise ValueError("incomplete")
        size = int(data[i:end].split(b";")[0], 16)  # ';' পরে chunk extension থাকতে পারে
        i = end + 2
        if size == 0:
            trailer_end = data.find(CRLF + CRLF, i - 2)
            if trailer_end < 0:
                raise ValueError("incomplete")
            return out, trailer_end + 4
        if len(data) < i + size + 2:
            raise ValueError("incomplete")
        out += data[i:i + size]
        i += size + 2


class Connection:
    """একটি TCP connection-এ একাধিক request (keep-alive)।"""

    def __init__(self, host: str, port: int, timeout: float = 5.0) -> None:
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""
        self.raw_log: list[bytes] = []

    def _fill(self) -> bool:
        chunk = self.sock.recv(65536)
        if chunk:
            self.buf += chunk
            self.raw_log.append(chunk)
        return bool(chunk)

    def request(self, raw: bytes, method: str = "GET") -> Response:
        self.sock.sendall(raw)
        while CRLF + CRLF not in self.buf:
            if not self._fill():
                raise ValueError("connection closed before headers")
        head, self.buf = self.buf.split(CRLF + CRLF, 1)
        resp = parse_head(head)
        if method == "HEAD" or resp.status in (204, 304) or 100 <= resp.status < 200:
            return resp
        if (resp.header("Transfer-Encoding") or "").lower() == "chunked":
            while True:
                try:
                    resp.body, used = decode_chunked(self.buf)
                    self.buf = self.buf[used:]
                    return resp
                except ValueError as exc:
                    if str(exc) != "incomplete" or not self._fill():
                        raise
        length = resp.header("Content-Length")
        if length is not None:
            n = int(length)
            while len(self.buf) < n:
                if not self._fill():
                    raise ValueError("connection closed mid-body")
            resp.body, self.buf = self.buf[:n], self.buf[n:]
            return resp
        while self._fill():  # কোনো length নেই: server connection বন্ধ করা পর্যন্ত পড়া
            pass
        resp.body, self.buf = self.buf, b""
        return resp

    def close(self) -> None:
        self.sock.close()


# --- demo-র জন্য local server ------------------------------------------------

class DemoHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive সমর্থন; default HTTP/1.0 প্রতিবার connection বন্ধ করে

    def log_message(self, *args: object) -> None:  # test output পরিষ্কার রাখতে
        pass

    def _send(self, status: int, body: bytes, extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/hello":
            self._send(200, b"hello\n")
        elif self.path == "/chunked":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for part in (b"line 1\n", b"line 2\n", b"done\n"):
                self.wfile.write(f"{len(part):x}\r\n".encode() + part + CRLF)
            self.wfile.write(b"0\r\n\r\n")
        elif self.path == "/old":
            self._send(301, b"moved\n", {"Location": "/hello"})
        else:
            self._send(404, b"not found\n")

    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        self._send(201, b"got " + str(len(data)).encode() + b" bytes\n")


def start_server() -> tuple[ThreadingHTTPServer, int]:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def stop_server(srv: ThreadingHTTPServer) -> None:
    srv.shutdown()
    srv.server_close()


def show(raw_out: bytes, resp: Response) -> None:
    print(">>> sent")
    text = raw_out.decode("latin-1").replace("\r\n", "\\r\\n\n")
    print(text if text.endswith("\n") else text + "\n", end="")
    print(f"<<< {resp.version} {resp.status} {resp.reason}")
    for k, v in resp.headers:
        print(f"    {k}: {v}")
    print(f"    body ({len(resp.body)} bytes): {resp.body[:200]!r}\n")


def demo() -> int:
    srv, port = start_server()
    try:
        conn = Connection("127.0.0.1", port)
        try:
            for method, path, body in (("GET", "/hello", b""), ("GET", "/chunked", b""),
                                       ("GET", "/old", b""), ("POST", "/hello", b"name=rahim"),
                                       ("GET", "/missing", b"")):
                raw = build_request(method, f"127.0.0.1:{port}", path, body=body)
                show(raw, conn.request(raw, method))
            print(f"all 5 requests reused ONE TCP connection (local port {conn.sock.getsockname()[1]})")
        finally:
            conn.close()
    finally:
        stop_server(srv)
    return 0


def get(url: str, show_raw: bool) -> int:
    u = urlsplit(url)
    if u.scheme != "http":
        print("error: only http:// (HTTPS needs TLS — see L02-08)", file=sys.stderr)
        return 2
    host, port = u.hostname or "", u.port or 80
    path = (u.path or "/") + (f"?{u.query}" if u.query else "")
    conn = Connection(host, port)
    try:
        raw = build_request("GET", u.netloc, path, keep_alive=False)
        resp = conn.request(raw)
    finally:
        conn.close()
    if show_raw:
        show(raw, resp)
    else:
        print(f"{resp.status} {resp.reason}  ({len(resp.body)} body bytes)")
    return 0 if resp.status < 400 else 1


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Raw HTTP/1.1 over a socket.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    g = sub.add_parser("get")
    g.add_argument("url")
    g.add_argument("--show-raw", action="store_true")
    args = p.parse_args(argv)
    try:
        return demo() if args.cmd == "demo" else get(args.url, args.show_raw)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
