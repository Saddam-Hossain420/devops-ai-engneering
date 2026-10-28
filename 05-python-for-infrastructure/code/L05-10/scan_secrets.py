#!/usr/bin/env python3
"""scan_secrets.py — repository-তে ভুলে রাখা secret খোঁজা (commit-এর আগে, বা CI-তে)।

  python3 scan_secrets.py .                       # সব text file
  python3 scan_secrets.py . --allowlist .secrets-allowlist
  python3 scan_secrets.py . --json

খোঁজে: private key block, AWS access key id, GitHub/Slack token, URL-এ password, WireGuard PrivateKey,
এবং password/secret/token = "দীর্ঘ মান" ধরনের assignment। মিলে যাওয়া মান output-এ mask করা থাকে।
মিথ্যা সতর্কতা দমন: একই লাইনে `scan-secrets: allow`, বা allowlist file-এ `path:rule` / `fingerprint`।
Exit: 0 কিছু পাওয়া যায়নি, 1 finding আছে, 2 argument error।

সীমা: এটা শেখার জন্য সরল scanner — Git history দেখে না (মুছে ফেলা secret history-তে থেকে যায়);
production-এ gitleaks / trufflehog / GitHub secret scanning ব্যবহার করুন (Module 19)।
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

RULES: dict[str, re.Pattern[str]] = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
    "aws-access-key-id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "slack-token": re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"),
    "url-password": re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:([^/\s:@]{4,})@"),
    "wireguard-private-key": re.compile(r"(?i)^\s*PrivateKey\s*=\s*([A-Za-z0-9+/]{42,43}=)"),
    "assignment": re.compile(
        # \b-এর পরে \w*: `db_password`-এ '_' ও 'p'-এর মাঝে word boundary নেই — \b একা হলে DB_PASSWORD বাদ পড়ত
        r"(?i)\b\w*(?:password|passwd|secret|token|api[_-]?key)\w*\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"),
}
PLACEHOLDER = re.compile(r"(?i)^(?:x+|\*+|\.+|changeme|example\w*|dummy\w*|placeholder|your[_-]?\w*|<[^>]+>"
                         r"|\$\{?\w+\}?|pass(?:word)?|passwd|token|secret|key)$")    # `user:TOKEN@` ধরনের documentation
# constant-এর নাম ("NOPASSWD") — আলাদা ও case-sensitive: (?i)-এর ভেতরে রাখলে যেকোনো অক্ষরের password বাদ পড়ত
CONSTANT_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache"}
INLINE_ALLOW = "scan-secrets: allow"
MAX_BYTES = 1_000_000


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    preview: str
    fingerprint: str


def mask(secret: str) -> str:
    return secret[:4] + "…" + f"({len(secret)} chars)" if len(secret) > 8 else "***"


def fingerprint(path: str, rule: str, secret: str) -> str:
    return hashlib.sha256(f"{path}\0{rule}\0{secret}".encode()).hexdigest()[:16]


def scan_text(text: str, rel: str) -> Iterator[Finding]:
    for n, line in enumerate(text.splitlines(), 1):
        if INLINE_ALLOW in line:
            continue
        for rule, pattern in RULES.items():
            for m in pattern.finditer(line):
                secret = m.group(1) if m.groups() else m.group(0)
                if rule in ("assignment", "url-password") and (PLACEHOLDER.match(secret)
                                                               or CONSTANT_NAME.match(secret)):
                    continue
                yield Finding(rel, n, rule, mask(secret), fingerprint(rel, rule, secret))


def iter_files(root: Path) -> Iterator[Path]:
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_BYTES:
            yield p


def load_allowlist(path: Path | None) -> tuple[set[str], set[tuple[str, str]]]:
    fps: set[str] = set()
    path_rules: set[tuple[str, str]] = set()
    if path is None:
        return fps, path_rules
    for raw in path.read_text(encoding="utf-8").splitlines():
        entry = raw.split("#", 1)[0].strip()
        if not entry:
            continue
        if re.fullmatch(r"[0-9a-f]{16}", entry):
            fps.add(entry)
        elif ":" in entry:
            p, rule = entry.rsplit(":", 1)
            path_rules.add((p.strip(), rule.strip()))
    return fps, path_rules


def scan(root: Path, allowlist: Path | None = None) -> tuple[list[Finding], int, int]:
    fps, path_rules = load_allowlist(allowlist)
    findings, allowed, files = [], 0, 0
    for p in iter_files(root):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue                                     # binary বা পড়া যায় না
        files += 1
        rel = p.relative_to(root).as_posix()
        for f in scan_text(text, rel):
            if f.fingerprint in fps or (f.path, f.rule) in path_rules:
                allowed += 1
            else:
                findings.append(f)
    return findings, allowed, files


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Find accidentally committed secrets.")
    ap.add_argument("root", type=Path)
    ap.add_argument("--allowlist", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not args.root.is_dir():
        print(f"error: not a directory: {args.root}", file=sys.stderr)
        return 2
    findings, allowed, files = scan(args.root, args.allowlist)
    if args.json:
        print(json.dumps({"files": files, "allowed": allowed, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.rule}: {f.preview}  [fp {f.fingerprint}]")
        print(f"scanned {files} files: {len(findings)} finding(s), {allowed} allowlisted", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
