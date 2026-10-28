#!/usr/bin/env python3
"""fcgi_client.py — ছোট FastCGI client: nginx-এর `fastcgi_pass` PHP-FPM-কে ঠিক যা পাঠায়, তা হাতে পাঠানো।

  python3 fcgi_client.py 127.0.0.1:9000 --script /var/www/wp/index.php --uri /index.php
  python3 fcgi_client.py 127.0.0.1:9000 --param SCRIPT_FILENAME=/var/www/wp/info.php --param REQUEST_METHOD=GET

FastCGI record (https://fast-cgi.github.io/spec): version 1, type, request id, content length, padding।
BEGIN_REQUEST (role RESPONDER) → PARAMS (name-value জোড়া) → খালি PARAMS → STDIN → খালি STDIN;
উত্তর: STDOUT (CGI header + body), STDERR, END_REQUEST।
"""
from __future__ import annotations

import argparse
import socket
import struct
import sys
from dataclasses import dataclass

FCGI_VERSION, BEGIN_REQUEST, END_REQUEST, PARAMS, STDIN, STDOUT, STDERR = 1, 1, 3, 4, 5, 6, 7
RESPONDER = 1


def record(rtype: int, content: bytes, request_id: int = 1) -> bytes:
    pad = -len(content) % 8
    return struct.pack(">BBHHBx", FCGI_VERSION, rtype, request_id, len(content), pad) + content + b"\x00" * pad


def name_value(name: bytes, value: bytes) -> bytes:
    def length(n: int) -> bytes:
        return struct.pack(">B", n) if n < 128 else struct.pack(">I", n | 0x80000000)
    return length(len(name)) + length(len(value)) + name + value


@dataclass
class Response:
    stdout: bytes
    stderr: bytes
    app_status: int

    @property
    def headers_and_body(self) -> tuple[dict[str, str], bytes]:
        head, _, body = self.stdout.partition(b"\r\n\r\n")
        headers = {}
        for line in head.decode("latin-1").split("\r\n"):
            k, _, v = line.partition(":")
            if k:
                headers[k.strip().lower()] = v.strip()
        return headers, body


def request(address: tuple[str, int], params: dict[str, str], body: bytes = b"", timeout: float = 10.0) -> Response:
    payload = record(BEGIN_REQUEST, struct.pack(">HB5x", RESPONDER, 0))       # flags 0: request শেষে connection বন্ধ
    encoded = b"".join(name_value(k.encode(), v.encode()) for k, v in params.items())
    for i in range(0, len(encoded), 65535):
        payload += record(PARAMS, encoded[i:i + 65535])
    payload += record(PARAMS, b"")
    if body:
        payload += record(STDIN, body)
    payload += record(STDIN, b"")
    out, err, status = bytearray(), bytearray(), -1
    with socket.create_connection(address, timeout=timeout) as s:
        s.sendall(payload)
        buf = b""
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
            while len(buf) >= 8:
                _, rtype, _, clen, pad = struct.unpack(">BBHHBx", buf[:8])
                if len(buf) < 8 + clen + pad:
                    break
                content, buf = buf[8:8 + clen], buf[8 + clen + pad:]
                if rtype == STDOUT:
                    out += content
                elif rtype == STDERR:
                    err += content
                elif rtype == END_REQUEST:
                    status = struct.unpack(">I", content[:4])[0]
    return Response(bytes(out), bytes(err), status)


def nginx_params(script_filename: str | None, uri: str, document_root: str, method: str = "GET") -> dict[str, str]:
    """nginx-এর fastcgi.conf মোটামুটি যা পাঠায়। script_filename=None = Ubuntu-র fastcgi_params-এর মতো (SCRIPT_FILENAME নেই)।"""
    path, _, query = uri.partition("?")
    params = {"GATEWAY_INTERFACE": "CGI/1.1", "SERVER_SOFTWARE": "nginx", "REQUEST_METHOD": method,
              "REQUEST_URI": uri, "DOCUMENT_URI": path, "SCRIPT_NAME": path, "QUERY_STRING": query,
              "DOCUMENT_ROOT": document_root, "SERVER_PROTOCOL": "HTTP/1.1", "REMOTE_ADDR": "127.0.0.1",
              "SERVER_NAME": "blog.example.com", "SERVER_PORT": "80", "REDIRECT_STATUS": "200"}
    if script_filename is not None:
        params["SCRIPT_FILENAME"] = script_filename
    return params


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Send one FastCGI request (like nginx fastcgi_pass).")
    ap.add_argument("address", help="HOST:PORT of PHP-FPM / php-cgi -b")
    ap.add_argument("--script", help="SCRIPT_FILENAME (omit to reproduce the fastcgi_params mistake)")
    ap.add_argument("--uri", default="/index.php")
    ap.add_argument("--root", default="/var/www/html")
    ap.add_argument("--param", action="append", default=[], help="extra/override NAME=VALUE")
    a = ap.parse_args(argv)
    host, _, port = a.address.rpartition(":")
    params = nginx_params(a.script, a.uri, a.root)
    params.update(dict(p.split("=", 1) for p in a.param))
    try:
        r = request((host, int(port)), params)
    except OSError as exc:
        print(f"error: cannot talk FastCGI to {a.address}: {exc}", file=sys.stderr)
        return 2
    headers, body = r.headers_and_body
    print(f"status: {headers.get('status', '200 (implicit)')}   app_status={r.app_status}")
    print(body.decode("utf-8", "replace").strip()[:1000])
    if r.stderr:
        print(f"stderr: {r.stderr.decode('utf-8', 'replace').strip()[:300]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
