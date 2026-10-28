#!/usr/bin/env python3
"""tls_conf_lint.py — nginx-এর TLS configuration-এর সাধারণ ভুল (L06-02-এর parser দিয়ে)।

  python3 tls_conf_lint.py taskflow-tls.conf

যাচাই: পুরোনো protocol (SSLv3/TLSv1/TLSv1.1), ssl_certificate-এ fullchain-এর বদলে শুধু cert (নাম দেখে অনুমান),
HTTPS server-এ HSTS নেই বা `always` নেই, port 80-এর HTTPS redirect নেই, `ssl_prefer_server_ciphers on` +
নিজস্ব দুর্বল cipher (RC4/3DES/NULL/EXPORT), `server_tokens`, private key world-readable path (/tmp)।
Exit: 0 কোনো error নেই, 1 error আছে, 2 file error।
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "L06-02"))
import nginx_conf as nc  # noqa: E402

OLD_PROTOCOLS = {"SSLv2", "SSLv3", "TLSv1", "TLSv1.1"}
WEAK_CIPHER = re.compile(r"(?i)\b(RC4|3DES|DES-CBC3|NULL|EXPORT|MD5)\b")


def where(d: nc.Directive) -> str:
    return f"{Path(d.file).name}:{d.line}"


def lint(tree: list[nc.Directive]) -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    servers = [d for _, d in nc.walk(tree) if d.name == "server" and d.block is not None]
    tls_servers = [s for s in servers if any("ssl" in x.args or "443" in " ".join(x.args) for x in s.find("listen"))]
    plain_servers = [s for s in servers if s not in tls_servers]

    for _, d in nc.walk(tree):
        if d.name == "ssl_protocols":
            old = sorted(set(d.args) & OLD_PROTOCOLS)
            if old:
                out.append(("error", where(d), "old-protocol", f"ssl_protocols allows {', '.join(old)} — use TLSv1.2 TLSv1.3"))
        if d.name == "ssl_ciphers" and d.args and WEAK_CIPHER.search(d.args[0]) and not re.search(r"!(RC4|3DES|NULL)", d.args[0]):
            out.append(("error", where(d), "weak-cipher", f"ssl_ciphers includes weak suites: {d.args[0][:60]}"))
        if d.name == "ssl_certificate" and d.args:
            name = Path(d.args[0]).name
            if "chain" not in name and name not in ("bundle.crt",) and not name.startswith("fullchain"):
                out.append(("warning", where(d), "maybe-no-chain",
                            f"ssl_certificate {name}: if this is the leaf only, clients without the intermediate fail "
                            "('unable to get local issuer certificate') — use fullchain.pem"))
        if d.name == "ssl_certificate_key" and d.args and d.args[0].startswith(("/tmp/", "/home/")):
            out.append(("warning", where(d), "key-location", f"private key in {d.args[0]} — keep it under /etc (root, 0600)"))
        if d.name == "server_tokens" and d.args[:1] == ["on"]:
            out.append(("warning", where(d), "server-tokens", "server_tokens on reveals the nginx version"))

    for s in tls_servers:
        hsts = [x for _, x in nc.walk(s.block or []) if x.name == "add_header" and x.args and
                x.args[0].lower() == "strict-transport-security"]
        if not hsts:
            out.append(("warning", where(s), "no-hsts", "HTTPS server without Strict-Transport-Security"))
        elif "always" not in hsts[0].args:
            out.append(("warning", where(hsts[0]), "hsts-not-always",
                        "add_header without 'always' is skipped on 4xx/5xx responses"))
        if s.first("ssl_certificate") is None and not any(x.name == "ssl_certificate" for _, x in nc.walk(tree)):
            out.append(("error", where(s), "no-certificate", "listen … ssl without ssl_certificate"))

    tls_names = {n for s in tls_servers for x in s.find("server_name") for n in x.args}
    for s in plain_servers:
        names = {n for x in s.find("server_name") for n in x.args}
        # redirect server-স্তরে বা কোনো location-এ (ACME challenge-এর path আলাদা রেখে) — দুটোই বৈধ
        redirects = any(x.name == "return" and x.args[:1] in (["301"], ["308"]) and "https://" in " ".join(x.args)
                        for _, x in nc.walk(s.block or []))
        if names & tls_names and not redirects:
            out.append(("warning", where(s), "no-https-redirect",
                        f"port-80 server for {', '.join(sorted(names & tls_names))} does not redirect to https"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint nginx TLS configuration.")
    ap.add_argument("config", type=Path)
    a = ap.parse_args(argv)
    try:
        findings = lint(nc.load(a.config))
    except (OSError, nc.ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for level, w, code, msg in findings:
        print(f"{level.upper():<7} {w:<26} {code:<18} {msg}")
    print(f"{len(findings)} finding(s)")
    return 1 if any(f[0] == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
