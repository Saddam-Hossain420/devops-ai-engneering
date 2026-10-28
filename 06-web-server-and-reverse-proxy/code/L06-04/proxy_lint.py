#!/usr/bin/env python3
"""proxy_lint.py — nginx reverse-proxy configuration-এর সাধারণ ভুল ধরে (L06-02-এর parser দিয়ে)।

  python3 proxy_lint.py taskflow-broken.conf
  python3 proxy_lint.py taskflow.conf --json

যাচাই: Host/X-Forwarded-* header, upstream keepalive-এর শর্ত (HTTP/1.1 + Connection ""), `localhost` upstream,
timeout-এর মান, client_max_body_size, upstream-এ max_fails, proxy_set_header-এর inheritance ফাঁদ।
Exit: 0 কোনো error নেই, 1 error আছে, 2 file error। শুধু config পড়ে — nginx -t-এর বিকল্প নয়।
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "L06-02"))
import nginx_conf as nc  # noqa: E402

WANTED_HEADERS = {"host": "Host", "x-forwarded-for": "X-Forwarded-For", "x-forwarded-proto": "X-Forwarded-Proto"}


@dataclass(frozen=True)
class Finding:
    level: str
    where: str
    code: str
    message: str


def seconds(value: str) -> float | None:
    m = re.fullmatch(r"(\d+)(ms|s|m|h)?", value)
    if not m:
        return None
    return int(m.group(1)) * {"ms": 0.001, None: 1, "s": 1, "m": 60, "h": 3600}[m.group(2)]


def where(d: nc.Directive) -> str:
    return f"{Path(d.file).name}:{d.line}"


def headers_in(block: list[nc.Directive]) -> dict[str, str]:
    return {d.args[0].lower(): " ".join(d.args[1:]) for d in block if d.name == "proxy_set_header" and d.args}


def lint(tree: list[nc.Directive]) -> list[Finding]:
    out: list[Finding] = []
    upstreams = {d.args[0]: d for _, d in nc.walk(tree) if d.name == "upstream" and d.block is not None and d.args}

    for name, up in upstreams.items():
        servers = up.find("server")
        keepalive = up.first("keepalive")
        for s in servers:
            if s.args and s.args[0].split(":")[0] == "localhost":
                out.append(Finding("warning", where(s), "localhost-upstream",
                                   f"upstream {name}: 'localhost' may resolve to ::1 first; if the app listens only "
                                   "on 127.0.0.1 every request first fails on [::1] — use 127.0.0.1"))
        if len(servers) > 1 and not any("max_fails" in " ".join(s.args) for s in servers):
            out.append(Finding("warning", where(up), "no-max-fails",
                               f"upstream {name}: several servers but default max_fails=1/fail_timeout=10s — decide explicitly"))
        if keepalive is not None:
            users = [(ctx, d) for ctx, d in nc.walk(tree) if d.name == "location" and d.block is not None
                     and any(p.name == "proxy_pass" and name in p.args[0] for p in d.block if p.args)]
            for _, loc in users:
                version = loc.first("proxy_http_version")
                conn = headers_in(loc.block or []).get("connection")
                if version is None or version.args[:1] != ["1.1"] or conn != '""' and conn != "":
                    out.append(Finding("error", where(loc), "keepalive-unused",
                                       f"upstream {name} has keepalive but this location lacks "
                                       "'proxy_http_version 1.1;' and 'proxy_set_header Connection \"\";' — "
                                       "connections are not reused"))

    for _ctx, d in nc.walk(tree):
        if d.name == "location" and d.block is not None and d.first("proxy_pass") is not None:
            pp = d.first("proxy_pass")
            assert pp is not None
            target = pp.args[0] if pp.args else ""
            host = re.sub(r"^https?://", "", target).split("/")[0].split(":")[0]
            if host == "localhost":
                out.append(Finding("warning", where(pp), "localhost-upstream",
                                   "proxy_pass to 'localhost' may try ::1 first — use 127.0.0.1 (or a unix socket)"))
            local = headers_in(d.block)
            inherited = {}
            parent_blocks = [b for c, b in nc.walk(tree) if b.block is not None and d in (b.block or [])]
            for p in parent_blocks:
                inherited = headers_in(p.block or [])
            effective = local if local else inherited                          # একটিও থাকলে বাইরেরগুলো হারায়
            if local and inherited and set(inherited) - set(local):
                lost = sorted(WANTED_HEADERS.get(h, h) for h in set(inherited) - set(local))
                out.append(Finding("error", where(d), "proxy-header-inheritance",
                                   f"location sets its own proxy_set_header, so the server-level ones are dropped: "
                                   f"{', '.join(lost)}"))
            missing = [v for k, v in WANTED_HEADERS.items() if k not in effective]
            if missing:
                out.append(Finding("warning", where(d), "missing-forward-headers",
                                   f"proxy without {', '.join(missing)} — the app sees nginx's address/host, not the client's"))
            for name in ("proxy_read_timeout", "proxy_connect_timeout", "proxy_send_timeout"):
                t = d.first(name)
                if t is not None and t.args:
                    v = seconds(t.args[0])
                    if v is not None and v > 300:
                        out.append(Finding("warning", where(t), "timeout-too-long",
                                           f"{name} {t.args[0]} — slow upstream ties up connections; prefer async jobs"))

    if not any(d.name == "client_max_body_size" for _, d in nc.walk(tree)):
        out.append(Finding("warning", "-", "default-body-size",
                           "client_max_body_size not set — default 1m; larger uploads get 413 from nginx"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint an nginx reverse-proxy configuration.")
    ap.add_argument("config", type=Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        tree = nc.load(a.config)
    except (OSError, nc.ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = lint(tree)
    if a.json:
        print(json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False))
    else:
        for f in findings:
            print(f"{f.level.upper():<7} {f.where:<22} {f.code:<26} {f.message}")
        print(f"{len(findings)} finding(s)")
    return 1 if any(f.level == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
