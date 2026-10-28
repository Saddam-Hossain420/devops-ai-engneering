#!/usr/bin/env python3
"""cert_expiry.py — certificate file বা live server-এর মেয়াদ কত দিন বাকি; monitoring-এর exit code সহ।

  python3 cert_expiry.py /etc/letsencrypt/live/*/fullchain.pem --warn-days 21 --crit-days 7
  python3 cert_expiry.py --host taskflow.example.com:443 --host api.example.com

Exit (L05-08-এর রীতি): 0 OK, 1 WARNING, 2 CRITICAL (মেয়াদ শেষ বা crit-এর কম), 3 UNKNOWN (পড়া যায়নি)।
File-এর জন্য openssl CLI লাগে; live check শুধু Python ssl (মেয়াদ দেখার জন্য verify বন্ধ — শুধু তারিখ পড়ে)।
"""
from __future__ import annotations

import argparse
import socket
import ssl
import subprocess
import sys
import time
from datetime import UTC, datetime

OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3
SEVERITY = {OK: 0, WARNING: 1, UNKNOWN: 2, CRITICAL: 3}
NAMES = {OK: "OK", WARNING: "WARNING", CRITICAL: "CRITICAL", UNKNOWN: "UNKNOWN"}


def not_after_from_file(path: str) -> datetime:
    r = subprocess.run(["openssl", "x509", "-noout", "-enddate", "-in", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise ValueError(r.stderr.strip().splitlines()[0] if r.stderr.strip() else "openssl failed")
    value = r.stdout.strip().split("=", 1)[1]                       # notAfter=Nov 26 08:10:10 2026 GMT
    return datetime.fromtimestamp(ssl.cert_time_to_seconds(value), UTC)


def not_after_from_host(target: str, timeout: float = 5.0) -> datetime:
    host, _, port = target.partition(":")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE                                  # মেয়াদোত্তীর্ণ cert-ও পড়তে চাই
    with socket.create_connection((host, int(port or 443)), timeout=timeout) as raw, \
            ctx.wrap_socket(raw, server_hostname=host) as tls:
        der = tls.getpeercert(binary_form=True)
    if not der:
        raise ValueError("no certificate")
    pem = ssl.DER_cert_to_PEM_cert(der)
    r = subprocess.run(["openssl", "x509", "-noout", "-enddate"], input=pem, capture_output=True, text=True)
    if r.returncode != 0:
        raise ValueError("openssl could not parse the peer certificate")
    return datetime.fromtimestamp(ssl.cert_time_to_seconds(r.stdout.strip().split("=", 1)[1]), UTC)


def classify(not_after: datetime, warn: int, crit: int, now: datetime | None = None) -> tuple[int, float]:
    days = (not_after - (now or datetime.now(UTC))).total_seconds() / 86400
    if days < crit:
        return CRITICAL, days
    if days < warn:
        return WARNING, days
    return OK, days


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Days until certificate expiry, with monitoring exit codes.")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--host", action="append", default=[], help="HOST[:PORT] to check live")
    ap.add_argument("--warn-days", type=int, default=21)
    ap.add_argument("--crit-days", type=int, default=7)
    a = ap.parse_args(argv)
    if not a.files and not a.host:
        ap.error("give certificate files and/or --host")
    worst = OK
    for kind, target in [("file", f) for f in a.files] + [("host", h) for h in a.host]:
        start = time.monotonic()
        try:
            na = not_after_from_file(target) if kind == "file" else not_after_from_host(target)
            status, days = classify(na, a.warn_days, a.crit_days)
            detail = f"{days:7.1f} days left (notAfter {na:%Y-%m-%d %H:%M}Z)"
        except (OSError, ValueError, ssl.SSLError) as exc:
            status, detail = UNKNOWN, f"cannot read: {exc}"
        worst = max(worst, status, key=SEVERITY.__getitem__)
        print(f"{NAMES[status]:<9} {target:<40} {detail}  [{(time.monotonic() - start) * 1000:.0f} ms]")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
