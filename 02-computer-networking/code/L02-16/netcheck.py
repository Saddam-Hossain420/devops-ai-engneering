#!/usr/bin/env python3
"""স্তর ধরে network diagnosis: DNS → TCP → TLS → HTTP। প্রথম যে স্তর ব্যর্থ হয় সেখানে থামে এবং
পরের command সুপারিশ করে। শুধু standard library।

  python3 netcheck.py https://example.com/
  python3 netcheck.py http://127.0.0.1:8000/health --timeout 2
  python3 netcheck.py https://api.internal:8443/ --json        # automation/monitoring-এর জন্য

Exit: 0 সব স্তর ঠিক, 1 কোনো স্তর ব্যর্থ বা HTTP 5xx, 2 input error।
"""
from __future__ import annotations

import argparse
import errno
import json
import socket
import ssl
import sys
import time
from dataclasses import asdict, dataclass, field
from urllib.parse import urlsplit

HINTS = {
    "dns": "dig NAME; resolvectl status; getent hosts NAME; cat /etc/hosts  (L02-06)",
    "tcp-refused": "nothing listening or a firewall REJECT: on the server `ss -ltnp | grep PORT`; check bind address (L02-05, L02-10)",
    "tcp-timeout": "packets dropped on the way (firewall DROP, security group, NACL, route): "
                   "traceroute -T -p PORT HOST; tcpdump on both ends (L02-10, L02-14, L02-15)",
    "tcp-unreachable": "no route to the host/network: ip route get IP; check VPN/peering routes (L02-04, L02-14)",
    "tls": "openssl s_client -connect HOST:PORT -servername HOST; check chain, name, expiry (L02-08)",
    "http": "curl -v URL; check the server/proxy logs with the request id (L02-07, L02-12)",
}


@dataclass
class Step:
    layer: str
    ok: bool
    ms: float
    detail: str


@dataclass
class Report:
    url: str
    steps: list[Step] = field(default_factory=list)
    hint: str = ""

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.steps)


def classify(exc: OSError) -> str:
    """Socket error → কোন ধরনের TCP সমস্যা।"""
    if isinstance(exc, ConnectionRefusedError) or exc.errno in (errno.ECONNREFUSED, 10061):
        return "tcp-refused"
    if isinstance(exc, TimeoutError) or exc.errno in (errno.ETIMEDOUT, 10060):
        return "tcp-timeout"
    if exc.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH, 10065, 10051):
        return "tcp-unreachable"
    return "tcp-timeout" if "timed out" in str(exc) else "tcp-unreachable"


def ms_since(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def check(url: str, timeout: float = 5.0, cafile: str | None = None) -> Report:
    u = urlsplit(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("URL must look like http(s)://host[:port]/path")
    host, port = u.hostname, u.port or (443 if u.scheme == "https" else 80)
    path = (u.path or "/") + (f"?{u.query}" if u.query else "")
    r = Report(url)

    # 1. DNS — getaddrinfo application-এর মতোই resolve করে (/etc/hosts, nsswitch সহ; dig-এর মতো নয়)
    t0 = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        r.steps.append(Step("dns", False, ms_since(t0), f"{host}: {exc.strerror}"))
        r.hint = HINTS["dns"]
        return r
    addrs = list(dict.fromkeys(i[4][0] for i in infos))
    r.steps.append(Step("dns", True, ms_since(t0), f"{host} → {', '.join(addrs[:4])}"))

    # 2. TCP — প্রতিটি address চেষ্টা (curl-এর মতো), প্রথম সফলটি নেওয়া
    sock, errors = None, []
    for family, stype, proto, _, sa in infos:
        t0 = time.perf_counter()
        s = socket.socket(family, stype, proto)
        s.settimeout(timeout)
        try:
            s.connect(sa)
            sock = s
            r.steps.append(Step("tcp", True, ms_since(t0), f"connected to {sa[0]}:{port}"))
            break
        except OSError as exc:
            s.close()
            errors.append((sa[0], exc, ms_since(t0)))
    if sock is None:
        ip, exc, ms = errors[-1]
        kind = classify(exc)
        r.steps.append(Step("tcp", False, ms, f"{ip}:{port} {kind.split('-')[1]} ({exc})"))
        r.hint = HINTS[kind]
        return r

    try:
        # 3. TLS
        if u.scheme == "https":
            ctx = ssl.create_default_context(cafile=cafile)
            t0 = time.perf_counter()
            try:
                sock = ctx.wrap_socket(sock, server_hostname=host)
            except (ssl.SSLError, OSError) as exc:
                msg = exc.verify_message if isinstance(exc, ssl.SSLCertVerificationError) else str(exc)
                r.steps.append(Step("tls", False, ms_since(t0), msg))
                r.hint = HINTS["tls"]
                return r
            cert = sock.getpeercert()
            days = (ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) / 86400
            r.steps.append(Step("tls", True, ms_since(t0), f"{sock.version()}, certificate valid {days:.0f} more days"))

        # 4. HTTP — status line পর্যন্ত (time to first byte)
        t0 = time.perf_counter()
        req = (f"GET {path} HTTP/1.1\r\nHost: {u.netloc}\r\nUser-Agent: netcheck/1.0\r\n"
               "Connection: close\r\n\r\n").encode()
        try:
            sock.sendall(req)
            first = sock.recv(4096).split(b"\r\n", 1)[0].decode("latin-1")
        except OSError as exc:
            r.steps.append(Step("http", False, ms_since(t0), f"no response: {exc}"))
            r.hint = HINTS["http"]
            return r
        parts = first.split(" ", 2)
        if len(parts) < 2 or not parts[1].isdigit():
            r.steps.append(Step("http", False, ms_since(t0), f"not an HTTP response: {first[:60]!r}"))
            r.hint = HINTS["http"]
            return r
        status = int(parts[1])
        r.steps.append(Step("http", status < 500, ms_since(t0), f"{first}  (time to first byte)"))
        if status >= 500:
            r.hint = HINTS["http"]
        return r
    finally:
        sock.close()


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Layer-by-layer check of an HTTP(S) endpoint.")
    ap.add_argument("url")
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--cafile")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        r = check(args.url, args.timeout, args.cafile)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({**asdict(r), "ok": r.ok}, ensure_ascii=False))
    else:
        for s in r.steps:
            print(f"{'PASS' if s.ok else 'FAIL'}  {s.layer:<5} {s.ms:>8.1f} ms  {s.detail}")
        if r.hint:
            print(f"next: {r.hint}")
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
