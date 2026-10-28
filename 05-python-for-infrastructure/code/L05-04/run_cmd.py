#!/usr/bin/env python3
"""run_cmd.py — বাইরের command নিরাপদভাবে চালানো: list argument (shell নয়), timeout-এ পুরো process tree বন্ধ,
structured ফল, output-এর সীমা।

  python3 run_cmd.py --timeout 5 -- df -h /
  python3 run_cmd.py --timeout 2 --json -- sleep 10        # timed_out: true, returncode 124

Library হিসেবে:
  from run_cmd import run
  r = run(["systemctl", "is-active", "nginx"], timeout=5)
  if r.ok: ...

Return code-এর রীতি (coreutils `timeout` ও shell-এর মতো): 124 timeout, 126 চালানো যায়নি, 127 পাওয়া যায়নি।
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass

TIMEOUT_RC, CANNOT_EXEC_RC, NOT_FOUND_RC = 124, 126, 127


@dataclass
class Result:
    cmd: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool = False
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    @property
    def cmdline(self) -> str:
        return shlex.join(self.cmd)          # log-এ copy-paste করার মতো, সঠিক quoting সহ


def _kill_tree(proc: subprocess.Popen[str]) -> None:
    """Child ও তার সব descendant বন্ধ — নইলে grandchild pipe খোলা রাখে এবং অপেক্ষা চলতেই থাকে।"""
    if os.name == "posix":
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True, timeout=10, check=False)
        proc.kill()


def _cap(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit] + f"\n…[truncated {len(text) - limit} chars]", True


def run(cmd: Sequence[str], *, timeout: float = 30.0, cwd: str | None = None,
        extra_env: Mapping[str, str] | None = None, input_text: str | None = None,
        max_output: int = 1_000_000) -> Result:
    if isinstance(cmd, str):
        raise TypeError("pass a list of arguments, not a string (no shell)")
    argv = [str(a) for a in cmd]
    env = {**os.environ, **extra_env} if extra_env else None
    group = ({"start_new_session": True} if os.name == "posix"
             else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP})
    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            argv, cwd=cwd, env=env, text=True, encoding="utf-8", errors="replace",
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, **group)
    except FileNotFoundError:
        return Result(argv, NOT_FOUND_RC, "", f"command not found: {argv[0]}", 0.0)
    except PermissionError as exc:
        return Result(argv, CANNOT_EXEC_RC, "", f"cannot execute {argv[0]}: {exc.strerror}", 0.0)

    timed_out = False
    try:
        out, err = proc.communicate(input_text, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:                    # কোনো descendant তবুও pipe ধরে আছে
            out, err = "", "(output unavailable after kill)"
    duration = round(time.monotonic() - start, 3)
    out, t1 = _cap(out or "", max_output)
    err, t2 = _cap(err or "", max_output)
    rc = TIMEOUT_RC if timed_out else proc.returncode
    return Result(argv, rc, out, err, duration, timed_out, t1 or t2)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Run a command safely with a timeout.")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="command after --")
    args = ap.parse_args(argv)
    cmd = args.cmd[1:] if args.cmd[:1] == ["--"] else args.cmd
    if not cmd:
        ap.error("no command given (use: run_cmd.py [options] -- cmd args...)")
    r = run(cmd, timeout=args.timeout)
    if args.json:
        print(json.dumps({**asdict(r), "ok": r.ok, "cmdline": r.cmdline}, ensure_ascii=False, indent=2))
    else:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        status = "TIMEOUT" if r.timed_out else f"rc={r.returncode}"
        print(f"[{status} in {r.duration_s}s] {r.cmdline}", file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
