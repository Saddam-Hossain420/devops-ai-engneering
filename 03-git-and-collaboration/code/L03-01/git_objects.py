#!/usr/bin/env python3
"""Git object model নিজের হাতে — blob hash, loose object পড়া/লেখা, tree ও commit parse, ref resolve।
শুধু standard library (hashlib, zlib); `git` command ছাড়াই `.git` directory পড়ে।

  python3 git_objects.py hash README.md                       # = git hash-object README.md
  python3 git_objects.py refs   --git-dir .git                 # HEAD, branch, tag
  python3 git_objects.py cat    --git-dir .git HEAD             # commit/tree/blob/tag দেখা
  python3 git_objects.py log    --git-dir .git HEAD -n 5        # first-parent history
  python3 git_objects.py walk   --git-dir .git HEAD             # commit → tree → blob পুরো গাছ

সীমাবদ্ধতা: শুধু loose object (packfile নয় — `git gc`-এর পরে object pack-এ চলে যায়; তখন `git cat-file`)।
শেখার tool; production-এ `git cat-file`, `git ls-tree`, `git rev-parse`।
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import zlib
from pathlib import Path


def hash_object(data: bytes, kind: str = "blob") -> str:
    """Object ID = SHA-1("<type> <size>\\0" + content)। একই content → একই ID, সব machine-এ।"""
    return hashlib.sha1(f"{kind} {len(data)}".encode() + b"\x00" + data).hexdigest()


def object_path(git_dir: Path, sha: str) -> Path:
    return git_dir / "objects" / sha[:2] / sha[2:]


def read_object(git_dir: Path, sha: str) -> tuple[str, bytes]:
    p = object_path(git_dir, sha)
    if not p.exists():
        raise KeyError(f"{sha}: not a loose object (packed? try `git cat-file -p {sha}`)")
    raw = zlib.decompress(p.read_bytes())
    header, _, body = raw.partition(b"\x00")
    kind, size = header.decode().split(" ")
    if int(size) != len(body):
        raise ValueError(f"{sha}: size mismatch — corrupt object")
    if hash_object(body, kind) != sha:
        raise ValueError(f"{sha}: content does not match its hash — corrupt object")
    return kind, body


def write_object(git_dir: Path, data: bytes, kind: str = "blob") -> str:
    """`git hash-object -w`-এর সমতুল্য। Object অপরিবর্তনীয়: আগে থাকলে আবার লেখা হয় না।"""
    sha = hash_object(data, kind)
    p = object_path(git_dir, sha)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(zlib.compress(f"{kind} {len(data)}".encode() + b"\x00" + data))
    return sha


def parse_tree(body: bytes) -> list[tuple[str, str, str]]:
    """Tree entry binary: "<mode> <name>\\0<20-byte raw sha>" বারবার। (mode, name, hex sha)।"""
    out, i = [], 0
    while i < len(body):
        sp = body.index(b" ", i)
        nul = body.index(b"\x00", sp)
        mode, name = body[i:sp].decode(), body[sp + 1:nul].decode("utf-8", "replace")
        out.append((mode.zfill(6), name, body[nul + 1:nul + 21].hex()))
        i = nul + 21
    return out


def parse_commit(body: bytes) -> dict:
    """Header লাইন (tree, parent*, author, committer, …), খালি লাইন, message।"""
    head, _, message = body.decode("utf-8", "replace").partition("\n\n")
    info: dict = {"parents": [], "message": message}
    for line in head.splitlines():
        if line.startswith(" "):        # gpgsig-এর continuation লাইন
            continue
        key, _, value = line.partition(" ")
        if key == "parent":
            info["parents"].append(value)
        else:
            info[key] = value
    return info


def resolve(git_dir: Path, name: str) -> str:
    """HEAD / branch / tag / পূর্ণ sha → commit sha। Symbolic ref ও packed-refs অনুসরণ করে।"""
    if len(name) == 40 and all(c in "0123456789abcdef" for c in name):
        return name
    candidates = [name, f"refs/heads/{name}", f"refs/tags/{name}"]
    for ref in candidates:
        p = git_dir / ref
        if p.is_file():
            content = p.read_text().strip()
            if content.startswith("ref: "):             # HEAD → refs/heads/main
                return resolve(git_dir, content[5:])
            return peel(git_dir, content)
    packed = git_dir / "packed-refs"
    if packed.exists():
        for line in packed.read_text().splitlines():
            if line and line[0] not in "#^":
                sha, ref = line.split(" ", 1)
                if ref in candidates:
                    return peel(git_dir, sha)
    raise KeyError(f"cannot resolve {name!r}")


def peel(git_dir: Path, sha: str) -> str:
    """Annotated tag object হলে যে commit-কে নির্দেশ করে সেখানে পৌঁছানো।"""
    try:
        kind, body = read_object(git_dir, sha)
    except KeyError:
        return sha
    if kind == "tag":
        return peel(git_dir, body.split(b"\n", 1)[0].split(b" ")[1].decode())
    return sha


def list_refs(git_dir: Path) -> list[tuple[str, str]]:
    out = []
    head = (git_dir / "HEAD").read_text().strip()
    out.append(("HEAD", head))
    for p in sorted((git_dir / "refs").rglob("*")):
        if p.is_file():
            out.append((p.relative_to(git_dir).as_posix(), p.read_text().strip()))
    return out


def walk(git_dir: Path, sha: str, indent: str = "", name: str = "") -> list[str]:
    kind, body = read_object(git_dir, sha)
    label = f"{indent}{kind:6} {sha[:10]}  {name}".rstrip()
    if kind == "commit":
        c = parse_commit(body)
        return [f"{label}  \"{c['message'].strip().splitlines()[0]}\""] + walk(git_dir, c["tree"], indent + "  ", "(root tree)")
    if kind == "tree":
        lines = [label]
        for mode, child, csha in parse_tree(body):
            if mode == "160000":                       # submodule — অন্য repository-র commit
                lines.append(f"{indent}  commit {csha[:10]}  {child} (submodule)")
            else:
                lines += walk(git_dir, csha, indent + "  ", f"{child}" + ("/" if mode == "040000" else ""))
        return lines
    return [f"{label}  ({len(body)} bytes)"]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Read Git objects without git.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hash")
    h.add_argument("file", type=Path)
    for name in ("refs", "cat", "log", "walk"):
        s = sub.add_parser(name)
        s.add_argument("--git-dir", type=Path, default=Path(".git"))
        if name != "refs":
            s.add_argument("rev", nargs="?", default="HEAD")
        if name == "log":
            s.add_argument("-n", type=int, default=10)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "hash":
            print(hash_object(args.file.read_bytes()))
        elif args.cmd == "refs":
            for ref, value in list_refs(args.git_dir):
                print(f"{ref:30} {value}")
        elif args.cmd == "cat":
            sha = resolve(args.git_dir, args.rev)
            kind, body = read_object(args.git_dir, sha)
            print(f"{kind} {sha} ({len(body)} bytes)")
            if kind == "tree":
                for mode, name, csha in parse_tree(body):
                    print(f"{mode} {csha}  {name}")
            else:
                print(body.decode("utf-8", "replace"), end="" if body.endswith(b"\n") else "\n")
        elif args.cmd == "log":
            sha = resolve(args.git_dir, args.rev)
            for _ in range(args.n):
                c = parse_commit(read_object(args.git_dir, sha)[1])
                print(f"{sha[:10]} {c['message'].strip().splitlines()[0]}  (parents: {len(c['parents'])})")
                if not c["parents"]:
                    break
                sha = c["parents"][0]
        elif args.cmd == "walk":
            print("\n".join(walk(args.git_dir, resolve(args.git_dir, args.rev))))
    except (OSError, KeyError, ValueError) as exc:
        msg = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc  # KeyError-এর str-এ quote আসে
        print(f"error: {msg}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
