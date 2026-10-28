#!/usr/bin/env python3
"""TLS inspection — certificate, chain, hostname ও expiry যাচাই, শুধু standard library (+ lab-এ openssl CLI)।

Commands:
  python3 tls_inspect.py inspect example.com                  # system CA store দিয়ে verify
  python3 tls_inspect.py inspect internal.lan --port 8443 --cafile ca.crt --warn-days 30
  python3 tls_inspect.py lab                                  # temp dir-এ নিজের CA + server cert, loopback-এ
                                                              # ৩টি পরিস্থিতি: OK, hostname mismatch, untrusted CA

Exit: 0 OK, 1 verify ব্যর্থ বা expiry-র কাছাকাছি, 2 input/network error।
Lab-এর private key শুধু temporary directory-তে থাকে এবং শেষে মুছে যায় — repository-তে কখনো নয়।
"""
from __future__ import annotations

import argparse
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TlsInfo:
    version: str
    cipher: str
    subject: str
    issuer: str
    san: list[str]
    not_after: str
    days_left: float


def _name(rdns: tuple) -> str:
    """getpeercert()-এর ((('commonName', 'x'),), ...) → 'commonName=x, ...'."""
    return ", ".join(f"{k}={v}" for rdn in rdns for k, v in rdn)


def days_left(not_after: str, now: float | None = None) -> float:
    """'Jan  5 12:00:00 2027 GMT' → এখন থেকে কত দিন বাকি (ঋণাত্মক = মেয়াদ শেষ)।"""
    now = time.time() if now is None else now
    return (ssl.cert_time_to_seconds(not_after) - now) / 86400


def client_context(cafile: str | None = None) -> ssl.SSLContext:
    """Verify চালু (CERT_REQUIRED + check_hostname) — create_default_context-এর default।"""
    ctx = ssl.create_default_context(cafile=cafile)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def inspect(host: str, port: int = 443, cafile: str | None = None, server_name: str | None = None,
            timeout: float = 5.0) -> TlsInfo:
    """TLS handshake করে verified certificate-এর তথ্য। Verify ব্যর্থ হলে ssl.SSLCertVerificationError।"""
    ctx = client_context(cafile)
    with socket.create_connection((host, port), timeout=timeout) as raw:
        with ctx.wrap_socket(raw, server_hostname=server_name or host) as tls:  # SNI + hostname check
            cert = tls.getpeercert()
            cipher = tls.cipher()
            version = tls.version() or "?"
    san = [f"{t}:{v}" for t, v in cert.get("subjectAltName", ())]
    return TlsInfo(version, cipher[0] if cipher else "?", _name(cert.get("subject", ())),
                   _name(cert.get("issuer", ())), san, cert["notAfter"], days_left(cert["notAfter"]))


# --- lab: নিজের CA ও server certificate ---------------------------------------

def openssl_bin() -> str | None:
    return shutil.which("openssl")


def make_ca_and_leaf(d: Path, cn: str = "localhost", days: int = 30) -> dict[str, Path]:
    """openssl CLI দিয়ে: CA (self-signed) → leaf CSR → CA দিয়ে sign (SAN সহ)। EC P-256 key।"""
    exe = openssl_bin()
    if not exe:
        raise RuntimeError("openssl not found")
    p = {k: d / f"{k}" for k in ("ca.key", "ca.crt", "leaf.key", "leaf.csr", "leaf.crt", "ext.cnf")}

    def run(*args: str) -> None:
        subprocess.run([exe, *args], check=True, capture_output=True)

    run("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
        "-keyout", str(p["ca.key"]), "-out", str(p["ca.crt"]), "-subj", "/CN=Lab Root CA", "-days", str(days),
        "-addext", "basicConstraints=critical,CA:TRUE", "-addext", "keyUsage=critical,keyCertSign,cRLSign")
    run("req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
        "-keyout", str(p["leaf.key"]), "-out", str(p["leaf.csr"]), "-subj", f"/CN={cn}")
    p["ext.cnf"].write_text(f"subjectAltName=DNS:{cn},IP:127.0.0.1\nextendedKeyUsage=serverAuth\n"
                            "basicConstraints=CA:FALSE\n", encoding="ascii")
    run("x509", "-req", "-in", str(p["leaf.csr"]), "-CA", str(p["ca.crt"]), "-CAkey", str(p["ca.key"]),
        "-CAcreateserial", "-out", str(p["leaf.crt"]), "-days", str(days), "-extfile", str(p["ext.cnf"]))
    return p


def start_tls_server(certfile: Path, keyfile: Path) -> tuple[socket.socket, int, threading.Event]:
    """Loopback TLS server: প্রতিটি client-কে ছোট HTTP উত্তর দেয়। (socket, port, stop event)।"""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_cert_chain(str(certfile), str(keyfile))
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    srv.settimeout(0.2)
    stop = threading.Event()

    def loop() -> None:
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except (TimeoutError, OSError):
                continue
            try:
                with ctx.wrap_socket(conn, server_side=True) as tls:
                    tls.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n")
            except (ssl.SSLError, OSError):  # client verify ব্যর্থ হলে handshake ভাঙে — প্রত্যাশিত
                conn.close()

    threading.Thread(target=loop, daemon=True).start()
    return srv, srv.getsockname()[1], stop


def print_info(label: str, info: TlsInfo) -> None:
    print(f"{label}")
    print(f"  protocol  {info.version}   cipher {info.cipher}")
    print(f"  subject   {info.subject}")
    print(f"  issuer    {info.issuer}")
    print(f"  SAN       {', '.join(info.san) or '-'}")
    print(f"  expires   {info.not_after}  ({info.days_left:.1f} days left)")


def lab() -> int:
    if not openssl_bin():
        print("error: openssl not found (Ubuntu: sudo apt install openssl)", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="tls-lab-") as tmp:
        p = make_ca_and_leaf(Path(tmp))
        srv, port, stop = start_tls_server(p["leaf.crt"], p["leaf.key"])
        try:
            cases = (("1) trusted CA + correct name", str(p["ca.crt"]), "localhost"),
                     ("2) trusted CA + WRONG name (api.example.com)", str(p["ca.crt"]), "api.example.com"),
                     ("3) system CA store only (lab CA not trusted)", None, "localhost"))
            for label, cafile, name in cases:
                try:
                    print_info(label + "  -> OK", inspect("127.0.0.1", port, cafile, name))
                except ssl.SSLCertVerificationError as exc:
                    print(f"{label}  -> FAILED: {exc.verify_message}")
                print()
        finally:
            stop.set()
            srv.close()
    print("temporary keys and certificates deleted")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Inspect TLS certificates.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inspect")
    i.add_argument("host")
    i.add_argument("--port", type=int, default=443)
    i.add_argument("--cafile")
    i.add_argument("--server-name", help="SNI/hostname to verify (default: host)")
    i.add_argument("--warn-days", type=float, default=21)
    sub.add_parser("lab")
    args = ap.parse_args(argv)
    if args.cmd == "lab":
        return lab()
    try:
        info = inspect(args.host, args.port, args.cafile, args.server_name)
    except ssl.SSLCertVerificationError as exc:
        print(f"VERIFY FAILED: {exc.verify_message}", file=sys.stderr)
        return 1
    except (ssl.SSLError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print_info(f"{args.host}:{args.port}", info)
    if info.days_left < args.warn_days:
        print(f"WARNING: certificate expires in {info.days_left:.1f} days (< {args.warn_days})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
