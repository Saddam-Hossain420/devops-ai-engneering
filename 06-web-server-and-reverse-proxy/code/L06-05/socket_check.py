#!/usr/bin/env python3
"""socket_check.py — একটি user (যেমন nginx-এর www-data) কি এই unix socket-এ connect করতে পারবে? কেন নয়?

  python3 socket_check.py /run/taskflow/taskflow.sock --user www-data          # Linux: আসল stat
  python3 socket_check.py /home/ana/app/app.sock --user www-data --fake-fs layout.json   # যেকোনো OS: বর্ণনা থেকে

Unix socket-এ connect করতে লাগে: path-এর প্রতিটি directory-তে execute (search, 'x') অনুমতি,
এবং socket file-এ write ('w') অনুমতি (Linux)। nginx-এ এর ব্যর্থতা: "connect() to unix:… failed (13: Permission denied)"।
--fake-fs JSON: {"users": {"www-data": {"uid": 33, "groups": [33]}},
                 "paths": {"/home": {"uid": 0, "gid": 0, "mode": "0755", "type": "dir"}, ...}}
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class Node:
    path: str
    uid: int
    gid: int
    mode: int
    kind: str                     # dir / socket / file / missing


@dataclass(frozen=True)
class Identity:
    name: str
    uid: int
    groups: frozenset[int]


def allowed(node: Node, who: Identity, bit: str) -> tuple[bool, str]:
    """bit: 'r'/'w'/'x'। root সব পারে (directory-র x সহ, Linux-এ)।"""
    if who.uid == 0:
        return True, "root"
    shift = {"r": 2, "w": 1, "x": 0}[bit]
    if node.uid == who.uid:
        return bool(node.mode >> (6 + shift) & 1), "owner"
    if node.gid in who.groups:
        return bool(node.mode >> (3 + shift) & 1), "group"
    return bool(node.mode >> shift & 1), "other"


def check(socket_path: str, who: Identity, lookup) -> tuple[bool, list[str]]:
    lines: list[str] = []
    blocked: list[str] = []
    parts = PurePosixPath(socket_path).parts
    for i in range(1, len(parts) + 1):
        path = str(PurePosixPath(*parts[:i]))
        node = lookup(path)
        last = i == len(parts)
        if node.kind == "missing":
            lines.append(f"  {path:<34} MISSING")
            return False, lines + [f"verdict: {path} does not exist (app not running? wrong path?)"]
        need = "w" if last else "x"
        good, via = allowed(node, who, need)
        mode = stat.filemode(node.mode | (stat.S_IFSOCK if node.kind == "socket" else
                                          stat.S_IFDIR if node.kind == "dir" else stat.S_IFREG))
        mark = "ok " if good else "NO "
        lines.append(f"  {mark} {mode} uid={node.uid:<5} gid={node.gid:<5} {path:<34} needs '{need}' as {via}")
        if last and node.kind != "socket":
            lines.append(f"verdict: {path} is a {node.kind}, not a socket")
            return False, lines
        if not good:
            blocked.append(path)
    ok = not blocked
    if ok:
        lines.append(f"verdict: {who.name} can connect")
    else:
        lines.append(f"verdict: {who.name} is blocked at {', '.join(blocked)} — nginx logs '(13: Permission denied)'")
    return ok, lines


def real_lookup(path: str) -> Node:
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return Node(path, -1, -1, 0, "missing")
    kind = "socket" if stat.S_ISSOCK(st.st_mode) else "dir" if stat.S_ISDIR(st.st_mode) else "file"
    return Node(path, st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode), kind)


def real_identity(name: str) -> Identity:
    import grp
    import pwd
    pw = pwd.getpwnam(name)
    groups = {pw.pw_gid} | {g.gr_gid for g in grp.getgrall() if name in g.gr_mem}
    return Identity(name, pw.pw_uid, frozenset(groups))


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Can USER connect to a unix socket? Walks every path component.")
    ap.add_argument("socket")
    ap.add_argument("--user", default="www-data")
    ap.add_argument("--fake-fs", help="JSON description instead of the real filesystem (any OS)")
    a = ap.parse_args(argv)
    if a.fake_fs:
        with open(a.fake_fs, encoding="utf-8") as f:
            spec = json.load(f)
        u = spec["users"][a.user]
        who = Identity(a.user, u["uid"], frozenset(u["groups"]))

        def lookup(path: str) -> Node:
            n = spec["paths"].get(path)
            return Node(path, n["uid"], n["gid"], int(n["mode"], 8), n["type"]) if n else Node(path, -1, -1, 0, "missing")
    else:
        if os.name != "posix":
            print("error: real filesystem check needs Linux; use --fake-fs on this OS", file=sys.stderr)
            return 2
        try:
            who = real_identity(a.user)
        except KeyError:
            print(f"error: no such user {a.user}", file=sys.stderr)
            return 2
        lookup = real_lookup
    ok, lines = check(a.socket, who, lookup)
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
