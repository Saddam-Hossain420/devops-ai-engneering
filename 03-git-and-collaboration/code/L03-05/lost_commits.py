#!/usr/bin/env python3
""""হারিয়ে যাওয়া" commit খোঁজা — reflog-এ আছে কিন্তু কোনো branch/tag/remote থেকে পৌঁছানো যায় না।
(reset --hard, branch মুছে ফেলা, rebase/amend-এর পরে পুরোনো commit।) শুধু পড়ে, কিছু বদলায় না।

  python3 lost_commits.py                     # বর্তমান repository
  python3 lost_commits.py --repo /tmp/x --fsck    # reflog-এর বাইরেও: git fsck-এর unreachable commit

প্রতিটি পাওয়া commit-এর জন্য উদ্ধারের command ছাপে (চালায় না):  git branch rescue/<sha> <sha>
Exit: 0 কিছু হারায়নি, 1 উদ্ধারযোগ্য commit পাওয়া গেছে, 2 error।
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def reachable(repo: Path) -> set[str]:
    """সব ref (branch, tag, remote, stash) থেকে পৌঁছানো commit।"""
    return set(git(repo, "rev-list", "--all").split())


def reflog_entries(repo: Path) -> list[tuple[str, str, str]]:
    """(sha, selector, বিবরণ) — সব ref-এর reflog, নতুন থেকে পুরোনো।"""
    out = git(repo, "log", "-g", "--all", "--format=%H%x09%gd%x09%gs")
    rows = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def lost_from_reflog(repo: Path) -> list[tuple[str, str, str]]:
    """Reflog-এর যেসব commit-এ এখন কোনো ref পৌঁছায় না; একই commit একবার (সবচেয়ে নতুন entry)।
    শুধু "tip"-গুলো রাখা হয় — অন্য একটি হারানো commit-এর পূর্বপুরুষ হলে বাদ (একটি branch-ই সব উদ্ধার করে)।"""
    live, seen, lost = reachable(repo), set(), []
    for sha, sel, desc in reflog_entries(repo):
        if sha not in live and sha not in seen:
            seen.add(sha)
            lost.append((sha, sel, desc))
    tips = []
    for sha, sel, desc in lost:
        ancestors_of_others = any(
            o != sha and subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, o]).returncode == 0
            for o, _, _ in lost)
        if not ancestors_of_others:
            tips.append((sha, sel, desc))
    return tips


def unreachable_from_fsck(repo: Path) -> list[str]:
    """Reflog মুছে গেলেও object থাকতে পারে (gc-র আগে পর্যন্ত)। "dangling" = unreachable এবং অন্য কোনো
    unreachable commit-ও একে নির্দেশ করে না — অর্থাৎ শুধু tip (`--unreachable` দিলে পুরো চেইন আসত)।"""
    out = git(repo, "fsck", "--no-reflogs")
    return [line.split()[2] for line in out.splitlines() if line.startswith("dangling commit ")]


def describe(repo: Path, sha: str) -> str:
    return git(repo, "log", "-1", "--format=%h %ad %s", "--date=short", sha).strip()


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Find commits that no branch or tag points to any more.")
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--fsck", action="store_true", help="also search objects not in any reflog")
    args = ap.parse_args(argv)
    try:
        lost = lost_from_reflog(args.repo)
        for sha, sel, desc in lost:
            print(f"{describe(args.repo, sha)}")
            print(f"    reflog: {sel}  ({desc})")
            print(f"    recover: git branch rescue/{sha[:7]} {sha[:12]}")
        extra = []
        if args.fsck:
            known = {s for s, _, _ in lost}
            extra = [s for s in unreachable_from_fsck(args.repo) if s not in known]
            for sha in extra:
                print(f"{describe(args.repo, sha)}")
                print(f"    found by git fsck (not in any reflog)")
                print(f"    recover: git branch rescue/{sha[:7]} {sha[:12]}")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {(getattr(exc, 'stderr', '') or str(exc)).strip()}", file=sys.stderr)
        return 2
    total = len(lost) + len(extra)
    print(f"{total} recoverable commit tip(s)" if total else "nothing lost: every reflog commit is still reachable")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
