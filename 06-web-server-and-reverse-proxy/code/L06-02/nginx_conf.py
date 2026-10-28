#!/usr/bin/env python3
"""nginx_conf.py — nginx configuration-এর ছোট parser (শেখার জন্য) ও capacity হিসাব। nginx install না থাকলেও চলে।

  python3 nginx_conf.py dump sample-nginx.conf                 # directive tree (include সহ)
  python3 nginx_conf.py get sample-nginx.conf worker_connections
  python3 nginx_conf.py capacity sample-nginx.conf --cpus 4 --nofile 1024

Parser নিয়ম (nginx-এর মতো): directive `;` দিয়ে শেষ, block `{ }`, `#` comment (quote-এর বাইরে), single/double quote,
`include` (glob, config file-এর directory-র সাপেক্ষে)। এটা `nginx -t`-এর বিকল্প নয় — module-এর নিজস্ব নিয়ম জানে না।
এই module-এর পরের lesson-গুলো (L06-03 …) এই parser import করে।
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path


class ConfError(Exception):
    pass


@dataclass
class Directive:
    name: str
    args: list[str]
    line: int
    file: str
    block: list[Directive] | None = None          # None = সাধারণ directive; list = block
    children_by_name: dict[str, list[Directive]] = field(default_factory=dict, repr=False)

    def find(self, name: str) -> list[Directive]:
        return [d for d in (self.block or []) if d.name == name]

    def first(self, name: str) -> Directive | None:
        found = self.find(name)
        return found[0] if found else None


def tokenize(text: str, file: str = "<string>") -> Iterator[tuple[str, int, bool]]:
    """(token, line, quoted) — quoted token কখনো `;`/`{`/`}` হিসেবে গণ্য নয়।"""
    i, line, n = 0, 1, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
        elif ch.isspace():
            i += 1
        elif ch == "#":
            while i < n and text[i] != "\n":
                i += 1
        elif ch in "{};":
            yield ch, line, False
            i += 1
        elif ch in "\"'":
            quote, start_line, i, buf = ch, line, i + 1, []
            while i < n and text[i] != quote:
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == "\n":
                    line += 1
                buf.append(text[i])
                i += 1
            if i >= n:
                raise ConfError(f"{file}:{start_line}: unterminated quote")
            i += 1
            yield "".join(buf), start_line, True
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in "{};" and text[i] not in "\"'":
                if text[i] == "#" and i > start:          # nginx-এ শব্দের মাঝের # comment নয়
                    i += 1
                    continue
                i += 1
            yield text[start:i], line, False


def parse(text: str, file: str = "<string>", base: Path | None = None, depth: int = 0) -> list[Directive]:
    if depth > 10:
        raise ConfError(f"{file}: include nesting too deep (loop?)")
    tokens = list(tokenize(text, file))
    pos = 0

    def block(top: bool) -> list[Directive]:
        nonlocal pos
        out: list[Directive] = []
        words: list[str] = []
        start_line = 0
        while pos < len(tokens):
            tok, line, quoted = tokens[pos]
            pos += 1
            if not quoted and tok == ";":
                if not words:
                    raise ConfError(f"{file}:{line}: unexpected ';'")
                d = Directive(words[0], words[1:], start_line, file)
                if d.name == "include" and base is not None:
                    out.extend(include(d, base, depth))
                else:
                    out.append(d)
                words = []
            elif not quoted and tok == "{":
                if not words:
                    raise ConfError(f"{file}:{line}: block without a name")
                d = Directive(words[0], words[1:], start_line, file)
                d.block = block(top=False)
                out.append(d)
                words = []
            elif not quoted and tok == "}":
                if top:
                    raise ConfError(f"{file}:{line}: unexpected '}}'")
                if words:
                    raise ConfError(f"{file}:{line}: directive {words[0]!r} is not terminated by ';'")
                return out
            else:
                if not words:
                    start_line = line
                words.append(tok)
        if words:
            raise ConfError(f"{file}: unexpected end of file, expecting ';' or '}}' after {words[0]!r}")
        if not top:
            raise ConfError(f"{file}: unexpected end of file, expecting '}}'")
        return out

    return block(top=True)


def include(d: Directive, base: Path, depth: int) -> list[Directive]:
    if not d.args:
        raise ConfError(f"{d.file}:{d.line}: include needs a path")
    pattern = d.args[0] if os.path.isabs(d.args[0]) else str(base / d.args[0])
    paths = sorted(glob.glob(pattern))
    if not paths and not glob.has_magic(pattern):
        raise ConfError(f"{d.file}:{d.line}: include file not found: {d.args[0]}")
    out: list[Directive] = []
    for p in paths:                                   # glob মিললে কিছু না থাকলেও nginx error দেয় না
        out.extend(parse(Path(p).read_text(encoding="utf-8"), p, base, depth + 1))
    return out


def load(path: Path) -> list[Directive]:
    return parse(path.read_text(encoding="utf-8"), str(path), path.parent)


def walk(tree: list[Directive], ctx: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Directive]]:
    for d in tree:
        yield ctx, d
        if d.block is not None:
            yield from walk(d.block, (*ctx, d.name))


def capacity(tree: list[Directive], cpus: int, nofile: int, proxied: bool = True) -> dict[str, object]:
    def value(name: str, default: str) -> str:
        found = [d for _, d in walk(tree) if d.name == name]
        return found[-1].args[0] if found and found[-1].args else default

    wp = value("worker_processes", "1")
    workers = cpus if wp == "auto" else int(wp)
    wc = int(value("worker_connections", "512"))
    rlimit = int(value("worker_rlimit_nofile", str(nofile)))
    per_worker = min(wc, rlimit)                                    # fd সীমা connection-কে আটকায়
    conns = workers * per_worker
    clients = conns // 2 if proxied else conns                     # proxy: client ↔ nginx ↔ upstream = ২টি
    notes = []
    if rlimit < wc:
        notes.append(f"worker_connections {wc} > open-file limit {rlimit}: workers will hit "
                     f"'Too many open files' first — raise worker_rlimit_nofile / LimitNOFILE")
    if wp != "auto" and workers > cpus:
        notes.append(f"worker_processes {workers} > {cpus} CPUs: extra workers only add context switches")
    return {"workers": workers, "worker_connections": wc, "fd_limit_per_worker": rlimit,
            "max_connections": conns, "max_clients_estimate": clients, "proxied": proxied, "notes": notes}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Parse nginx config (learning tool) and estimate capacity.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("dump", "get", "capacity"):
        p = sub.add_parser(name)
        p.add_argument("config", type=Path)
        if name == "get":
            p.add_argument("directive")
        if name == "capacity":
            p.add_argument("--cpus", type=int, default=os.cpu_count() or 1)
            p.add_argument("--nofile", type=int, default=1024, help="ulimit -n of the worker (default 1024)")
            p.add_argument("--static", action="store_true", help="no proxying (1 connection per client)")
    args = ap.parse_args(argv)
    try:
        tree = load(args.config)
    except (OSError, ConfError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "dump":
        for ctx, d in walk(tree):
            indent = "  " * len(ctx)
            print(f"{indent}{d.name} {' '.join(d.args)}{' {' if d.block is not None else ''}"
                  f"   # {Path(d.file).name}:{d.line}")
    elif args.cmd == "get":
        for ctx, d in walk(tree):
            if d.name == args.directive:
                print(f"{'/'.join(ctx) or 'main'}: {d.name} {' '.join(d.args)}   ({Path(d.file).name}:{d.line})")
    else:
        print(json.dumps(capacity(tree, args.cpus, args.nofile, not args.static), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
