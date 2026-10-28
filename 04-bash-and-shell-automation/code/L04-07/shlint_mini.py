#!/usr/bin/env python3
"""shlint_mini — ShellCheck-এর কয়েকটি গুরুত্বপূর্ণ নিয়মের ছোট, শেখার জন্য লেখা রূপ। ShellCheck-এর বিকল্প নয়।

ShellCheck shell-এর পূর্ণ parser ব্যবহার করে শত শত নিয়ম পরীক্ষা করে; এই tool লাইন-ভিত্তিক regex দিয়ে
মাত্র ছয়টি পরীক্ষা করে — যেখানে ShellCheck নেই সেখানে প্রাথমিক জাল, এবং নিয়মগুলো কেন আছে তা বোঝার জন্য।

  python3 shlint_mini.py script.sh lib/*.sh
  python3 shlint_mini.py --list                  # নিয়মের তালিকা ও ShellCheck-এর সমতুল্য code

লাইনে নিয়ম বন্ধ:  rm -rf $dir   # shlint-disable=M001
Exit: 0 পরিষ্কার, 1 finding, 2 file পড়া যায়নি।
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RULES = {
    "M001": ("unquoted variable in a file/dir command (word splitting + glob)", "SC2086"),
    "M002": ("`local/export/declare/readonly x=$(...)` hides the command's exit status", "SC2155"),
    "M003": ("`cd` without a failure check in a script that lacks `set -e`", "SC2164"),
    "M004": ("looping over `$(ls ...)`/`$(find ...)` output breaks on spaces", "SC2045/SC2044"),
    "M005": ("`rm -rf \"$VAR/...\"` — if VAR is empty this becomes `/...`; use ${VAR:?}", "SC2115"),
    "M006": ("`read` without -r mangles backslashes", "SC2162"),
}
FILE_CMDS = r"(?:rm|mv|cp|chmod|chown|mkdir|rmdir|cd|tar|ln)"


def strip_quotes(line: str) -> str:
    """Quote-এর ভেতরের অংশ সরিয়ে দেয়। Double quote-এর ভেতরের $(...)-এ nested quote ("$(dirname -- "$x")")
    আলাদা করে মানে — প্রথম সংস্করণে এটা ছিল না, এবং এই module-এর নিজের script-এ false positive দিয়েছিল।
    তবু নিখুঁত নয়: পূর্ণ shell parser নয় (ShellCheck তা-ই ব্যবহার করে)।"""
    out, i, q, depth = [], 0, "", 0
    while i < len(line):
        c = line[i]
        if q:
            if c == "\\" and q == '"':
                i += 2
                continue
            if q == '"' and line.startswith("$(", i):
                depth += 1
                i += 2
                continue
            if q == '"' and depth and c == ")":
                depth -= 1
            elif q == '"' and depth and c == '"':
                end = line.find('"', i + 1)            # $(...)-এর ভেতরের nested string বাদ
                i = len(line) if end < 0 else end + 1
                continue
            elif c == q and not depth:
                q = ""
            i += 1
            continue
        if c in "\"'":
            q = c
            out.append("Q")              # quote-এর জায়গা চিহ্ন
        elif c == "#" and (i == 0 or line[i - 1] in " \t;"):
            break                        # comment
        else:
            out.append(c)
        i += 1
    return "".join(out)


def lint_text(text: str) -> list[tuple[int, str, str]]:
    lines = text.splitlines()
    has_set_e = any(re.match(r"\s*set\s+-[A-Za-z]*e", l) for l in lines)
    findings: list[tuple[int, str, str]] = []
    heredoc_end = None
    for n, raw in enumerate(lines, 1):
        if heredoc_end is not None:
            if raw.strip() == heredoc_end:
                heredoc_end = None
            continue
        m = re.search(r"<<-?\s*['\"]?([A-Za-z_]+)['\"]?", raw)
        if m and not raw.lstrip().startswith("#"):
            heredoc_end = m.group(1)
        disabled = set(re.findall(r"shlint-disable=([A-Z0-9,]+)", raw))
        disabled = {r for group in disabled for r in group.split(",")}
        code = strip_quotes(raw)
        if not code.strip():
            continue

        def add(rule: str) -> None:
            if rule not in disabled:
                findings.append((n, rule, raw.strip()))

        if re.search(rf"(?:^|[;&|(]\s*|\s)\b{FILE_CMDS}\b[^;|&]*?\$\{{?[A-Za-z_]", code):
            add("M001")
        if re.search(r"\b(?:local|export|declare|readonly)\s+(?:-\w+\s+)*\w+=\$\((?!\()", code.replace("Q", '"')) \
                or re.search(r"^\s*(?:local|export|declare|readonly)\s+(?:-\w+\s+)*\w+=\$\((?!\()", raw):
            add("M002")
        if not has_set_e and re.search(r"(?:^|[;&]\s*)cd\s", code) and "||" not in code and "$(" not in raw:
            add("M003")
        if re.search(r"\bfor\s+\w+\s+in\s+\$\((?:ls|find)\b", raw):
            add("M004")
        if re.search(r"\brm\s+-\w*r\w*\s+[\"']?\$\{?([A-Za-z_]\w*)\}?/", raw) and ":?" not in raw:
            add("M005")
        if re.search(r"(?:^|[;&|]\s*|\s)read\s+(?!.*-\w*r)", code):
            add("M006")
    return findings


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tiny shell linter (learning tool, not ShellCheck).")
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.list:
        for rule, (text, sc) in RULES.items():
            print(f"{rule}  ({sc:13}) {text}")
        return 0
    total = 0
    for f in args.files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: {f}: {exc.strerror}", file=sys.stderr)
            return 2
        for n, rule, src in lint_text(text):
            print(f"{f}:{n}: {rule} {RULES[rule][0]} [{RULES[rule][1]}]\n    {src}")
            total += 1
    print(f"{len(args.files)} file(s), {total} finding(s)")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
