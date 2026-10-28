#!/usr/bin/env python3
"""GitHub Actions workflow-এর নিরাপত্তা ও নির্ভরযোগ্যতা lint — শুধু standard library (YAML library ছাড়া,
লাইন ও indentation ধরে; পূর্ণ YAML parser নয়)।

  python3 workflow_lint.py .github/workflows/*.yml
  python3 workflow_lint.py sample-bad-workflow.yml

যা ধরে:
  ERROR  script injection — `run:`-এর ভেতরে ${{ github.event.* / github.head_ref }} সরাসরি
  ERROR  pull_request_target + PR-এর head code checkout
  ERROR  permissions: write-all
  WARN   top-level permissions নেই (GITHUB_TOKEN-এর default অধিকার বেশি হতে পারে)
  WARN   third-party action commit SHA দিয়ে pin করা নয় (tag সরানো যায়)
  WARN   secret সরাসরি echo/print
  WARN   job-এ timeout-minutes নেই
  INFO   workflow-এ concurrency নেই
Exit: 0 কোনো ERROR/WARN নেই, 1 finding, 2 input error।
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SHA_PIN = re.compile(r"@[0-9a-f]{40}$")
# Attacker নিয়ন্ত্রিত context — issue/PR-এর title, body, comment, branch name ইত্যাদি
TAINTED = re.compile(r"\$\{\{\s*(github\.event\.(issue|pull_request|comment|review|review_comment|discussion|"
                     r"head_commit|commits|pages|workflow_run)[^}]*|github\.head_ref)\s*\}\}")
SECRET_ECHO = re.compile(r"\b(echo|printf|print|cat)\b.*\$\{\{\s*secrets\.", re.IGNORECASE)


def indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def lint(text: str) -> list[str]:
    lines = text.splitlines()
    out: list[str] = []
    top_keys = {l.split(":")[0].strip().strip('"\'') for l in lines if l and not l.startswith((" ", "#", "-"))}

    if "permissions" not in top_keys:
        out.append("WARN  no top-level `permissions:` — set the least the workflow needs (e.g. contents: read)")
    if "concurrency" not in top_keys:
        out.append("INFO  no `concurrency:` — repeated pushes run in parallel and waste minutes")

    triggers = text.split("jobs:", 1)[0]
    prt = "pull_request_target" in triggers

    run_indent = None            # multi-line run block-এর ভেতরে থাকলে তার key-এর indentation
    in_jobs, job, job_indent, job_has_timeout, jobs = False, None, None, False, []
    for n, raw in enumerate(lines, 1):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        ind = indent(line)

        if run_indent is not None and ind <= run_indent:
            run_indent = None
        in_run_block = run_indent is not None

        # jobs ও প্রতিটি job-এর সীমানা
        if line.startswith("jobs:"):
            in_jobs = True
            continue
        if in_jobs and ind == 0:
            in_jobs = False
        if in_jobs and re.match(r"^\s+[A-Za-z0-9_-]+:\s*$", line) and (job_indent is None or ind == job_indent):
            if job is not None:
                jobs.append((job, job_has_timeout))
            job, job_indent, job_has_timeout = stripped[:-1], ind, False
            continue
        if job and stripped.startswith("timeout-minutes:"):
            job_has_timeout = True

        m_run = re.match(r"^\s*(?:-\s+)?run:\s*(.*)$", line)
        if m_run:
            value = m_run.group(1)
            if value in ("|", ">", "|-", ">-", "|+", ">+"):
                run_indent = indent(line) + (2 if line.lstrip().startswith("-") else 0)
            check_line = value
        elif in_run_block:
            check_line = stripped
        else:
            check_line = None

        if check_line is not None:
            if TAINTED.search(check_line):
                out.append(f"ERROR line {n}: untrusted `${{{{ github.event... }}}}` expanded inside `run:` — "
                           "script injection; pass it through `env:` and use \"$VAR\"")
            if SECRET_ECHO.search(check_line):
                out.append(f"WARN  line {n}: secret printed in `run:` — masking is best-effort; never echo secrets")

        m_uses = re.match(r"^\s*(?:-\s+)?uses:\s*['\"]?([^'\"\s#]+)", line)
        if m_uses:
            ref = m_uses.group(1)
            if not ref.startswith(("./", "docker://")) and not SHA_PIN.search(ref):
                out.append(f"WARN  line {n}: `{ref}` is pinned to a tag/branch, not a commit SHA — "
                           "a moved tag runs different code (pin: owner/action@<40-hex-sha> # vX.Y.Z)")
            if prt and ref.startswith("actions/checkout"):
                window = "\n".join(lines[n:n + 6])
                if re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request\.head", window):
                    out.append(f"ERROR line {n}: pull_request_target checks out the PR's code — untrusted code "
                               "runs with secrets and a write token")

        if re.match(r"^\s*permissions:\s*write-all\s*$", line):
            out.append(f"ERROR line {n}: `permissions: write-all` — grant only the scopes needed")

    if job is not None:
        jobs.append((job, job_has_timeout))
    for name, has in jobs:
        if not has:
            out.append(f"WARN  job `{name}` has no timeout-minutes — a hung job runs up to the 6-hour default")
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint GitHub Actions workflows for common security mistakes.")
    ap.add_argument("files", nargs="+", type=Path)
    args = ap.parse_args(argv)
    bad = 0
    for f in args.files:
        try:
            findings = lint(f.read_text(encoding="utf-8"))
        except OSError as exc:
            print(f"error: {f}: {exc.strerror}", file=sys.stderr)
            return 2
        print(f"{f}: {len(findings)} finding(s)")
        for x in findings:
            print(f"  {x}")
        bad += sum(not x.startswith("INFO") for x in findings)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
