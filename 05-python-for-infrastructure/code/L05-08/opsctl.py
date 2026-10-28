#!/usr/bin/env python3
"""opsctl.py — argparse দিয়ে ছোট ops CLI: subcommand, সাধারণ option, validation, exit code, JSON, pipe-বান্ধব।

  python3 opsctl.py disk / --warn 80 --crit 90
  python3 opsctl.py --json port 127.0.0.1:22 db.internal:5432 --timeout 2
  python3 opsctl.py disk / /var --json | jq '.checks[] | select(.status != "ok")'

Exit code (Nagios/monitoring-plugin রীতি): 0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN।
argparse-এর ভুল ব্যবহারে argparse নিজে 2 দেয় — তাই usage error-কে আমরা 64 (EX_USAGE)-এ বদলাই।
Ctrl-C → 130; `| head` দিয়ে pipe আগে বন্ধ হলে চুপচাপ বেরিয়ে যায়।
"""
from __future__ import annotations

import argparse
import errno
import json
import os
import shutil
import socket
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass

__version__ = "1.0.0"
OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3
EX_USAGE = 64
STATUS = {OK: "ok", WARNING: "warning", CRITICAL: "critical", UNKNOWN: "unknown"}
# গুরুত্বের ক্রম exit code-এর সংখ্যার ক্রম নয়: একটি CRITICAL disk একটি UNKNOWN-এর চেয়ে জরুরি
SEVERITY = {OK: 0, WARNING: 1, UNKNOWN: 2, CRITICAL: 3}


def worst(statuses: Sequence[int]) -> int:
    return max(statuses, key=SEVERITY.__getitem__, default=UNKNOWN)


@dataclass
class Check:
    name: str
    status: int
    detail: str
    value: float | None = None


# ---------- argument type validators: ভুল মান হলে argparse সুন্দর error দেয় ----------

def percent(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not 0 <= value <= 100:
        raise argparse.ArgumentTypeError(f"must be between 0 and 100, got {value:g}")
    return value


def host_port(text: str) -> tuple[str, int]:
    host, sep, port = text.rpartition(":")
    if not sep or not host or not port.isdigit() or not 0 < int(port) < 65536:
        raise argparse.ArgumentTypeError(f"expected HOST:PORT, got {text!r}")
    return host.strip("[]"), int(port)                     # [::1]:22 → ::1


def positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return value


# ---------- checks ----------

def check_disk(path: str, warn: float, crit: float) -> Check:
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        return Check(f"disk:{path}", UNKNOWN, exc.strerror or str(exc))
    used = round(100 * (usage.total - usage.free) / usage.total, 1)
    status = CRITICAL if used >= crit else WARNING if used >= warn else OK
    return Check(f"disk:{path}", status, f"{used}% used, {usage.free // 2**30} GiB free", used)


def check_port(target: tuple[str, int], timeout: float) -> Check:
    host, port = target
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            ms = round((time.monotonic() - start) * 1000, 1)
            return Check(f"port:{host}:{port}", OK, f"open in {ms} ms", ms)
    except TimeoutError:
        return Check(f"port:{host}:{port}", CRITICAL, f"timeout after {timeout}s")
    except OSError as exc:
        return Check(f"port:{host}:{port}", CRITICAL, exc.strerror or type(exc).__name__)


# ---------- parser ----------

def build_parser() -> argparse.ArgumentParser:
    # সাধারণ option: main ও প্রতিটি subcommand — দুই জায়গাতেই দেওয়া যায়।
    # SUPPRESS না দিলে subparser-এর default (False) main-এর `--json`-কে নীরবে মুছে দেয়।
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help="machine-readable output")
    common.add_argument("-q", "--quiet", action="store_true", default=argparse.SUPPRESS,
                        help="print only non-OK checks")

    ap = argparse.ArgumentParser(
        prog="opsctl", parents=[common],
        description="Small operations checks with monitoring-style exit codes.",
        epilog="exit codes: 0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN, 64 usage error\n"
               "examples:\n  opsctl disk / --warn 80 --crit 90\n  opsctl --json port 127.0.0.1:22",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="command", required=True, metavar="COMMAND")

    d = sub.add_parser("disk", parents=[common], help="filesystem usage")
    d.add_argument("paths", nargs="+", metavar="PATH")
    d.add_argument("--warn", type=percent, default=80.0, help="warning threshold %% (default 80)")
    d.add_argument("--crit", type=percent, default=90.0, help="critical threshold %% (default 90)")

    p = sub.add_parser("port", parents=[common], help="TCP port reachability")
    p.add_argument("targets", nargs="+", type=host_port, metavar="HOST:PORT")
    p.add_argument("--timeout", type=positive_float,
                   default=float(os.environ.get("OPSCTL_TIMEOUT", "3")),
                   help="seconds per connection (env OPSCTL_TIMEOUT, default 3)")
    return ap


def run(args: argparse.Namespace) -> list[Check]:
    if args.command == "disk":
        if args.warn >= args.crit:
            raise UsageError(f"--warn ({args.warn:g}) must be lower than --crit ({args.crit:g})")
        return [check_disk(path, args.warn, args.crit) for path in args.paths]
    return [check_port(t, args.timeout) for t in args.targets]


class UsageError(Exception):
    pass


def render(checks: list[Check], as_json: bool, quiet: bool) -> str:
    shown = [c for c in checks if not quiet or c.status != OK]
    if as_json:
        return json.dumps({"status": STATUS[worst([c.status for c in checks])], "checks": [{**asdict(c), "status": STATUS[c.status]}
                                                                for c in shown]}, indent=2)
    return "\n".join(f"{STATUS[c.status].upper():<9} {c.name:<28} {c.detail}" for c in shown)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:                      # --help/--version → 0; ভুল ব্যবহার → 2 → EX_USAGE
        return EX_USAGE if exc.code == 2 else int(exc.code or 0)
    try:
        checks = run(args)
    except UsageError as exc:
        parser.print_usage(sys.stderr)
        print(f"opsctl: error: {exc}", file=sys.stderr)
        return EX_USAGE
    output = render(checks, getattr(args, "json", False), getattr(args, "quiet", False))
    if output:
        print(output)
    return worst([c.status for c in checks])


def entrypoint() -> None:
    """pyproject-এর [project.scripts]-এর জন্য: Ctrl-C ও বন্ধ pipe পরিষ্কারভাবে সামলানো।"""
    try:
        code = main()
        sys.stdout.flush()
    except KeyboardInterrupt:
        code = 130
    except OSError as exc:                         # `opsctl ... | head -1` — পাঠক আগেই চলে গেছে
        # Linux: BrokenPipeError (EPIPE)। Windows: OSError EINVAL — একই ঘটনা, ভিন্ন error।
        if not isinstance(exc, BrokenPipeError) and exc.errno != errno.EINVAL:
            raise
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())      # interpreter বন্ধের সময় আবার flush-এ error নয়
        code = 141                                 # 128 + SIGPIPE(13), shell-এর রীতি; 0–3-এর সাথে সংঘাত নেই
    raise SystemExit(code)


if __name__ == "__main__":
    entrypoint()
