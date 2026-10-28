#!/usr/bin/env python3
"""server_select.py — একটি request কোন nginx `server` ও `location`-এ যাবে, nginx-এর documented নিয়মে হিসাব করে।

  python3 server_select.py sites.conf --host www.example.com --port 80 --uri /static/app.js
  python3 server_select.py sites.conf --port 80 --host 198.51.100.7          # IP দিয়ে এলে → default_server
  python3 server_select.py sites.conf --list                                  # সব listen ও server_name

Server নির্বাচন (https://nginx.org/en/docs/http/server_names.html, request_processing.html):
  ১. connection-এর address:port-এ যে server-গুলো listen করে (নির্দিষ্ট IP-র listen, *:port-এর চেয়ে আগে)
  ২. Host header: exact নাম → দীর্ঘতম "*.x" wildcard → দীর্ঘতম "x.*" wildcard → config-এর ক্রমে প্রথম regex
  ৩. কিছু না মিললে সেই listen-এর default_server, না থাকলে প্রথম server
Location নির্বাচন (https://nginx.org/en/docs/http/ngx_http_core_module.html#location):
  `=` exact → দীর্ঘতম prefix মনে রাখা → সেটা `^~` হলে থামা → regex (~, ~*) config-এর ক্রমে প্রথমটি → নইলে দীর্ঘতম prefix
এই tool L06-02-এর nginx_conf.py parser ব্যবহার করে। nested location ও `named location` (@) বিবেচনা করে না।
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "L06-02"))
import nginx_conf as nc  # noqa: E402


@dataclass
class Listen:
    addr: str            # "*" বা নির্দিষ্ট IP
    port: int
    default: bool


@dataclass
class Server:
    index: int
    directive: nc.Directive
    listens: list[Listen]
    names: list[str]

    @property
    def where(self) -> str:
        return f"{Path(self.directive.file).name}:{self.directive.line}"


def parse_listen(args: list[str]) -> Listen:
    target = args[0]
    default = "default_server" in args[1:] or "default" in args[1:]
    if target.startswith("["):                                     # [::]:80
        addr, _, port = target[1:].partition("]:")
        return Listen(addr or "*", int(port or 80), default)
    if target.isdigit():
        return Listen("*", int(target), default)
    addr, sep, port = target.rpartition(":")
    if not sep:                                                    # শুধু address — port 80
        return Listen(target, 80, default)
    return Listen("*" if addr in ("*", "0.0.0.0") else addr, int(port), default)


def servers_of(tree: list[nc.Directive]) -> list[Server]:
    out = []
    for _, d in nc.walk(tree):
        if d.name == "server" and d.block is not None:
            listens = [parse_listen(x.args) for x in d.find("listen")] or [Listen("*", 80, False)]
            names = [n.lower() for x in d.find("server_name") for n in x.args]
            out.append(Server(len(out), d, listens, names))
    return out


def pcre(pattern: str) -> str:
    """nginx PCRE-র named group `(?<name>…)` → Python-এর `(?P<name>…)`; lookbehind `(?<=`/`(?<!` অপরিবর্তিত।"""
    return re.sub(r"\(\?<(?![=!])", "(?P<", pattern)


def name_match(pattern: str, host: str) -> tuple[int, int] | None:
    """(শ্রেণি, দৈর্ঘ্য) — শ্রেণি: 0 exact, 1 leading wildcard, 2 trailing wildcard, 3 regex।"""
    if pattern.startswith("~"):
        return (3, 0) if re.search(pcre(pattern[1:]), host) else None
    if pattern.startswith("."):                                    # .example.com = example.com + *.example.com
        if host == pattern[1:]:
            return (0, len(pattern))
        return (1, len(pattern)) if host.endswith(pattern) else None
    if pattern.startswith("*."):
        return (1, len(pattern)) if host.endswith(pattern[1:]) else None
    if pattern.endswith(".*"):
        return (2, len(pattern)) if host.startswith(pattern[:-1]) else None
    return (0, len(pattern)) if host == pattern else None


def select_server(servers: list[Server], host: str, port: int, addr: str = "*") -> tuple[Server, str]:
    host = host.lower().split(":")[0].rstrip(".")                  # Host: www.Example.com.:80 → আগে port, তারপর শেষের dot
    candidates = [s for s in servers if any(l.port == port and l.addr == addr for l in s.listens)]
    if not candidates:                                             # নির্দিষ্ট IP-তে কেউ নেই → *:port
        candidates = [s for s in servers if any(l.port == port and l.addr == "*" for l in s.listens)]
    if not candidates:
        raise LookupError(f"no server listens on {addr}:{port}")
    best: tuple[tuple[int, int, int], Server, str] | None = None
    for s in candidates:
        for pattern in s.names:
            m = name_match(pattern, host)
            if m is None:
                continue
            klass, length = m
            # exact সবার আগে; wildcard-এ দীর্ঘতম; regex-এ config-এর প্রথমটি
            rank = (klass, -length, s.index) if klass < 3 else (klass, 0, s.index)
            if best is None or rank < best[0]:
                kind = ("exact", "leading wildcard", "trailing wildcard", "regex")[klass]
                best = (rank, s, f"server_name {pattern} ({kind})")
    if best:
        return best[1], best[2]
    defaults = [s for s in candidates if any(l.port == port and l.default for l in s.listens)]
    if defaults:
        return defaults[0], "default_server (no server_name matched)"
    return candidates[0], "first server for this port (no server_name matched, no default_server)"


def select_location(server: Server, uri: str) -> tuple[nc.Directive | None, str]:
    path = uri.split("?", 1)[0]
    locs = [d for d in server.directive.find("location") if d.block is not None]
    best_prefix: tuple[int, nc.Directive, str] | None = None
    for d in locs:
        if len(d.args) == 2 and d.args[0] == "=" and path == d.args[1]:
            return d, "exact match (=)"
        if len(d.args) == 1 or (len(d.args) == 2 and d.args[0] == "^~"):
            prefix = d.args[-1]
            if prefix.startswith("@"):
                continue
            if path.startswith(prefix) and (best_prefix is None or len(prefix) > best_prefix[0]):
                best_prefix = (len(prefix), d, "^~" if d.args[0] == "^~" else "prefix")
    if best_prefix and best_prefix[2] == "^~":
        return best_prefix[1], "longest prefix with ^~ (regex not checked)"
    for d in locs:
        if len(d.args) == 2 and d.args[0] in ("~", "~*"):
            flags = re.IGNORECASE if d.args[0] == "~*" else 0
            if re.search(pcre(d.args[1]), path, flags):
                return d, f"first matching regex ({d.args[0]})"
    if best_prefix:
        return best_prefix[1], "longest prefix (no regex matched)"
    return None, "no location matched → 404 unless server has root/return"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Which nginx server/location handles a request?")
    ap.add_argument("config", type=Path)
    ap.add_argument("--host", default="")
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--addr", default="*", help="local address the connection arrived on")
    ap.add_argument("--uri", default="/")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    try:
        servers = servers_of(nc.load(a.config))
    except (OSError, nc.ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.list:
        for s in servers:
            listens = ", ".join(f"{f'[{l.addr}]' if ':' in l.addr else l.addr}:{l.port}{' default' if l.default else ''}"
                                for l in s.listens)
            print(f"{s.where:<16} listen {listens:<24} server_name {' '.join(s.names) or '(none)'}")
        return 0
    try:
        server, why = select_server(servers, a.host, a.port, a.addr)
    except LookupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"server   {server.where}  ← {why}")
    server_return = server.directive.first("return")
    if server_return is not None:                       # server স্তরের return location-এর আগেই চলে (rewrite phase)
        print(f"return   {' '.join(server_return.args)}  ← server-level return runs before location matching")
        return 0
    loc, lwhy = select_location(server, a.uri)
    if loc is not None:
        print(f"location {' '.join(loc.args)}  ({Path(loc.file).name}:{loc.line})  ← {lwhy}")
        for d in loc.block or []:
            print(f"           {d.name} {' '.join(d.args)};")
    else:
        print(f"location -  ← {lwhy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
