#!/usr/bin/env python3
"""Lab 06-B verification — TaskFlow nginx-এর পেছনে (unix socket, systemd) ও HTTPS-এ।

  python3 check_b.py /etc/nginx/sites-available/taskflow.conf                     # config (যেকোনো OS)
  python3 check_b.py /etc/nginx/sites-available/taskflow.conf --live --cafile ~/lab06b/pki/root.crt

Offline: L06-04-এর proxy_lint ও L06-07-এর tls_conf_lint-এ কোনো error নেই; upstream unix socket; https redirect।
Live (VM): https://taskflow.example.com (127.0.0.1-এ resolve) — certificate যাচাই, /health 200, HSTS, X-Request-ID,
http → https 301, POST /tasks 201, এবং app সরাসরি port 8000-এ পৌঁছানো যায় না।
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import ssl
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for sub in ("L06-04", "L06-07"):
    sys.path.insert(0, str(REPO / "06-web-server-and-reverse-proxy" / "code" / sub))
import proxy_lint as pl  # noqa: E402
import tls_conf_lint as tl  # noqa: E402

NAME = "taskflow.example.com"


def offline(conf: Path) -> list[tuple[bool, str]]:
    tree = pl.nc.parse(conf.read_text(encoding="utf-8"), str(conf))
    proxy_errors = [f for f in pl.lint(tree) if f.level == "error"]
    tls_findings = tl.lint(tree)
    upstream_servers = [d.args[0] for _, d in pl.nc.walk(tree) if d.name == "server" and d.block is None and d.args]
    has_tls = any(d.name == "listen" and "ssl" in d.args for _, d in pl.nc.walk(tree))
    return [
        (has_tls, "an HTTPS server exists (listen 443 ssl) — otherwise the TLS checks below prove nothing"),
        (not proxy_errors, "proxy_lint: no errors" + (f" ({proxy_errors[0].code})" if proxy_errors else "")),
        (not [f for f in tls_findings if f[0] == "error"], "tls_conf_lint: no errors"),
        (not [f for f in tls_findings if f[2] in ("no-hsts", "hsts-not-always", "no-https-redirect")],
         "HSTS (always) and http → https redirect"),
        (any(s.startswith("unix:") for s in upstream_servers), "upstream uses a unix socket (L06-05)"),
    ]


def https(cafile: str, method: str, path: str, body: bytes | None = None) -> http.client.HTTPResponse:
    ctx = ssl.create_default_context(cafile=cafile)
    conn = http.client.HTTPSConnection("127.0.0.1", 443, timeout=5, context=ctx)
    conn.sock = ctx.wrap_socket(socket.create_connection(("127.0.0.1", 443), timeout=5), server_hostname=NAME)
    headers = {"Host": NAME}
    if body is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=body, headers=headers)
    return conn.getresponse()


def live(cafile: str) -> list[tuple[bool, str]]:
    out = []
    try:
        r = https(cafile, "GET", "/health")
        out.append((r.status == 200, f"https /health → {r.status} (certificate verified with the lab root)"))
        out.append(("max-age" in (r.getheader("Strict-Transport-Security") or ""), "HSTS header present"))
        out.append((bool(r.getheader("X-Request-ID")), "X-Request-ID returned"))
        r.read()
        r = https(cafile, "POST", "/tasks", json.dumps({"title": "lab 06-B"}).encode())
        out.append((r.status == 201, f"POST /tasks through nginx → {r.status}"))
    except (ssl.SSLError, OSError) as exc:
        out.append((False, f"https request failed: {exc}"))
    try:
        conn = http.client.HTTPConnection("127.0.0.1", 80, timeout=5)
        conn.request("GET", "/health", headers={"Host": NAME})
        r = conn.getresponse()
        out.append((r.status == 301 and (r.getheader("Location") or "").startswith("https://"),
                    f"http → {r.status} {r.getheader('Location')}"))
    except OSError as exc:
        out.append((False, f"http request failed: {exc}"))
    try:
        socket.create_connection(("127.0.0.1", 8000), timeout=2).close()
        out.append((False, "app is reachable directly on 127.0.0.1:8000 — it should only listen on the unix socket"))
    except OSError:
        out.append((True, "app not reachable on TCP 8000 (unix socket only)"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("config", type=Path)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--cafile", help="lab root CA (pki_lab.py create)")
    a = ap.parse_args()
    if a.live and not a.cafile:
        ap.error("--live needs --cafile")
    try:
        results = offline(a.config) + (live(a.cafile) if a.live else [])
    except (OSError, pl.nc.ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
