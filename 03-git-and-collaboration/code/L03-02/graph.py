#!/usr/bin/env python3
"""Commit graph বিশ্লেষণ — merge base, ahead/behind, fast-forward সম্ভব কিনা।
`git merge-base`, `git rev-list --left-right --count`, `git merge-base --is-ancestor`-এর ভেতরের ধারণা।

  python3 graph.py main feature          # বর্তমান repository-তে (git CLI থেকে graph পড়ে)
  python3 graph.py main feature --repo /tmp/merge-demo/demo

Exit: 0 OK, 2 error।
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from collections import deque
from pathlib import Path

Graph = dict[str, list[str]]   # commit → parents


def load_graph(repo: Path) -> Graph:
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--all", "--parents"],
                         capture_output=True, text=True, check=True).stdout
    g: Graph = {}
    for line in out.splitlines():
        sha, *parents = line.split()
        g[sha] = parents
    return g


def rev_parse(repo: Path, name: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{name}^{{commit}}"],
                          capture_output=True, text=True, check=True).stdout.strip()


def ancestors(g: Graph, start: str) -> set[str]:
    """start সহ তার সব পূর্বপুরুষ (BFS)।"""
    seen, queue = {start}, deque([start])
    while queue:
        for p in g.get(queue.popleft(), []):
            if p not in seen:
                seen.add(p)
                queue.append(p)
    return seen


def merge_bases(g: Graph, a: str, b: str) -> set[str]:
    """Best common ancestor: common ancestor যারা অন্য কোনো common ancestor-এর পূর্বপুরুষ নয়।
    সাধারণত একটি; criss-cross merge-এর পরে একাধিক হতে পারে (`git merge-base --all`)।"""
    common = ancestors(g, a) & ancestors(g, b)
    redundant = set()
    for c in common:
        redundant |= ancestors(g, c) - {c}
    return common - redundant


def ahead_behind(g: Graph, a: str, b: str) -> tuple[int, int]:
    """(a-তে আছে b-তে নেই, b-তে আছে a-তে নেই) — `git rev-list --left-right --count a...b`।"""
    aa, bb = ancestors(g, a), ancestors(g, b)
    return len(aa - bb), len(bb - aa)


def is_ancestor(g: Graph, a: str, b: str) -> bool:
    return a in ancestors(g, b)


def advice(g: Graph, target: str, source: str) -> str:
    if is_ancestor(g, source, target):
        return "already up to date: target contains source"
    if is_ancestor(g, target, source):
        return "fast-forward possible: target only needs to move its pointer (no merge commit)"
    return "diverged: needs a merge commit or a rebase of source onto target"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="How do two branches relate?")
    ap.add_argument("target", help="branch you merge INTO (e.g. main)")
    ap.add_argument("source", help="branch you merge FROM (e.g. feature)")
    ap.add_argument("--repo", type=Path, default=Path("."))
    args = ap.parse_args(argv)
    try:
        g = load_graph(args.repo)
        t, s = rev_parse(args.repo, args.target), rev_parse(args.repo, args.source)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or exc
        print(f"error: {str(detail).strip()}", file=sys.stderr)
        return 2
    ahead, behind = ahead_behind(g, s, t)
    bases = merge_bases(g, t, s)
    print(f"{args.source} is {ahead} commit(s) ahead and {behind} behind {args.target}")
    print(f"merge base: {', '.join(b[:10] for b in sorted(bases)) or 'none (unrelated histories)'}"
          + ("  ← more than one: criss-cross history" if len(bases) > 1 else ""))
    print(advice(g, t, s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
