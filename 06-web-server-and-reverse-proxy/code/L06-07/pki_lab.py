#!/usr/bin/env python3
"""pki_lab.py — lab PKI (root → intermediate → server) বানিয়ে nginx deployment-এর চারটি সাধারণ TLS ভুল আসলে দেখায়।

  python3 pki_lab.py scenarios                 # temp directory-তে সব বানিয়ে, loopback-এ TLS server চালিয়ে যাচাই
  python3 pki_lab.py create --out ./lab-pki    # শুধু file বানানো (Lab 06-B/C-তে ব্যবহার); key সেখানেই থাকে

Scenario: সঠিক fullchain · intermediate বাদ (leaf only) · chain-এর ভুল ক্রম · মেয়াদোত্তীর্ণ · ভুল key।
openssl CLI লাগে (Ubuntu: openssl package; Windows: Git-এর সাথে আসে)। সব key শুধু lab-এর জন্য, কোথাও ব্যবহার করবেন না;
`scenarios` শেষে temp directory মুছে যায়। repository-তে কোনো key রাখা হয় না।
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
from pathlib import Path

NAME = "taskflow.example.com"


def openssl(*args: str, cwd: Path) -> None:
    r = subprocess.run(["openssl", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"openssl {' '.join(args[:3])}… failed: {r.stderr.strip()[:300]}")


def write(cwd: Path, name: str, text: str) -> str:
    (cwd / name).write_text(text, encoding="utf-8")
    return name


def create(out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    ca_ext = write(out, "ca.ext", "basicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\n"
                                  "subjectKeyIdentifier=hash\n")
    int_ext = write(out, "int.ext", "basicConstraints=critical,CA:TRUE,pathlen:0\nkeyUsage=critical,keyCertSign,cRLSign\n"
                                    "subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid\n")
    leaf_ext = write(out, "leaf.ext", f"basicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature\n"
                                      f"extendedKeyUsage=serverAuth\nsubjectAltName=DNS:{NAME},DNS:www.{NAME}\n"
                                      "authorityKeyIdentifier=keyid\n")
    key = ("-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes")
    openssl("req", "-x509", *key, "-keyout", "root.key", "-out", "root.crt", "-days", "30",
            "-subj", "/CN=Lab Root CA (L06-07)", "-addext", "basicConstraints=critical,CA:TRUE",
            "-addext", "keyUsage=critical,keyCertSign,cRLSign", cwd=out)
    openssl("req", *key, "-keyout", "int.key", "-out", "int.csr", "-subj", "/CN=Lab Intermediate CA (L06-07)", cwd=out)
    openssl("x509", "-req", "-in", "int.csr", "-CA", "root.crt", "-CAkey", "root.key", "-CAcreateserial",
            "-out", "int.crt", "-days", "30", "-extfile", int_ext, cwd=out)
    openssl("req", *key, "-keyout", "server.key", "-out", "server.csr", "-subj", f"/CN={NAME}", cwd=out)
    openssl("x509", "-req", "-in", "server.csr", "-CA", "int.crt", "-CAkey", "int.key", "-CAcreateserial",
            "-out", "server.crt", "-days", "30", "-extfile", leaf_ext, cwd=out)
    openssl("x509", "-req", "-in", "server.csr", "-CA", "int.crt", "-CAkey", "int.key", "-CAcreateserial",
            "-out", "expired.crt", "-not_before", "20250101000000Z", "-not_after", "20250201000000Z",
            "-extfile", leaf_ext, cwd=out)
    openssl("req", *key, "-keyout", "other.key", "-out", "other.csr", "-subj", "/CN=unrelated", cwd=out)
    del ca_ext
    leaf, inter = (out / "server.crt").read_text(), (out / "int.crt").read_text()
    (out / "fullchain.pem").write_text(leaf + inter)                  # nginx-এর ssl_certificate: leaf আগে
    (out / "wrong-order.pem").write_text(inter + leaf)
    (out / "expired-fullchain.pem").write_text((out / "expired.crt").read_text() + inter)
    for tmp in ("int.csr", "server.csr", "other.csr", "ca.ext", "int.ext", "leaf.ext", "root.srl", "int.srl"):
        (out / tmp).unlink(missing_ok=True)
    return {p.name: p for p in out.iterdir()}          # stem নয়: root.crt ও root.key একই stem


def serve_once(certfile: Path, keyfile: Path) -> tuple[int, threading.Thread] | str:
    """TLS server (একটি handshake)। Certificate/key load-এ ব্যর্থ হলে সেটাই ফল — nginx-ও `nginx -t`-এ এখানে থামে।"""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.load_cert_chain(certfile, keyfile)
    except ssl.SSLError as exc:
        return f"server refuses to start: {exc.reason or exc}"
    srv = socket.create_server(("127.0.0.1", 0))

    def run() -> None:
        try:
            conn, _ = srv.accept()
            with ctx.wrap_socket(conn, server_side=True) as tls:
                tls.recv(1)
        except (OSError, ssl.SSLError):
            pass
        finally:
            srv.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return srv.getsockname()[1], t


def client(port: int, cafile: Path, name: str = NAME) -> str:
    ctx = ssl.create_default_context(cafile=str(cafile))              # শুধু lab root-কে বিশ্বাস — browser-এর মতো
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=5) as raw, \
                ctx.wrap_socket(raw, server_hostname=name) as tls:
            cert = tls.getpeercert()
            return f"OK {tls.version()} — notAfter {cert['notAfter']}"
    except ssl.SSLCertVerificationError as exc:
        return f"VERIFY FAILED: {exc.verify_message}"
    except (ssl.SSLError, OSError) as exc:
        return f"FAILED: {exc}"


def scenarios(d: Path) -> list[tuple[str, str]]:
    f = create(d)
    cases = [("fullchain (leaf + intermediate)", f["fullchain.pem"], f["server.key"]),
             ("leaf only — intermediate missing", f["server.crt"], f["server.key"]),
             ("wrong order (intermediate first)", f["wrong-order.pem"], f["server.key"]),
             ("expired leaf", f["expired-fullchain.pem"], f["server.key"]),
             ("key does not match certificate", f["fullchain.pem"], f["other.key"])]
    results = []
    for label, cert, key in cases:
        started = serve_once(cert, key)
        if isinstance(started, str):
            results.append((label, started))
            continue
        port, t = started
        results.append((label, client(port, f["root.crt"])))
        t.join(timeout=5)
    return results


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lab PKI and common nginx TLS deployment mistakes.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scenarios")
    c = sub.add_parser("create")
    c.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if shutil.which("openssl") is None:
        print("error: openssl not found", file=sys.stderr)
        return 2
    if a.cmd == "create":
        files = create(a.out)
        print("\n".join(sorted(str(p) for p in files.values())))
        return 0
    with tempfile.TemporaryDirectory(prefix="pki-lab-") as d:
        for label, result in scenarios(Path(d)):
            print(f"{label:<36} → {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
