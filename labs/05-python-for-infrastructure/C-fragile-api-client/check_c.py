#!/usr/bin/env python3
"""Lab 05-C verification — DIR/sync.py-কে ছয়টি পরিস্থিতিতে চালায় (নিজের chaos server, 127.0.0.1)।

  python3 check_c.py ~/lab05c            exit 0 = ALL CHECKS PASSED

প্রতিটি পরিস্থিতির আগে summary.json-এ একটি "আগের ভালো" সারাংশ রাখা হয় — ব্যর্থতায় তা অক্ষত থাকা উচিত।
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import chaos_server  # noqa: E402

PREVIOUS = {"total": 99, "done": 42, "fetched_at": "previous-good-run"}
MAX_SECONDS = 15


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("usage: python3 check_c.py DIR", file=sys.stderr)
        return 64
    dest = Path(sys.argv[1]).expanduser()
    if not (dest / ".lab05c").is_file():
        print(f"not a Lab 05-C directory: {dest}", file=sys.stderr)
        return 2
    sync, out = dest / "sync.py", dest / "summary.json"
    srv = chaos_server.serve(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    with socket.socket() as s:                                   # খালি port খুঁজে বন্ধ — "unreachable"
        s.bind(("127.0.0.1", 0))
        closed = f"http://127.0.0.1:{s.getsockname()[1]}"
    failed = 0

    def check(ok: bool, name: str, detail: str) -> None:
        nonlocal failed
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n      {detail}"))
        failed += not ok

    scenarios = [("ok", f"{base}/ok", True), ("flaky (503, 503, then ok)", f"{base}/flaky", True),
                 ("hang (no response for 60 s)", f"{base}/hang", False),
                 ("broken JSON body", f"{base}/broken", False),
                 ("HTML 502 from a proxy", f"{base}/html502", False), ("unreachable API", closed, False)]
    for name, url, should_succeed in scenarios:
        urllib.request.urlopen(f"{base}/reset", timeout=5).read()
        out.write_text(json.dumps(PREVIOUS), encoding="utf-8")
        before = set(dest.iterdir())
        start = time.monotonic()
        try:
            proc = subprocess.run([sys.executable, str(sync), url, str(out)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=MAX_SECONDS + 10)
            rc, err, stdout = proc.returncode, proc.stderr, proc.stdout
        except subprocess.TimeoutExpired:
            rc, err, stdout = None, "", ""
        took = time.monotonic() - start
        try:
            result = json.loads(out.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            result = "<missing or not JSON>"
        leftovers = sorted(p.name for p in set(dest.iterdir()) - before)

        check(rc is not None and took <= MAX_SECONDS, f"[{name}] finishes within {MAX_SECONDS}s",
              f"took {took:.1f}s" + (" (killed by checker)" if rc is None else ""))
        if should_succeed:
            check(rc == 0, f"[{name}] exit 0", f"exit {rc}; stderr: {err.strip()[:200]!r}")
            ok_summary = isinstance(result, dict) and result.get("total") == 3 and result.get("done") == 1
            check(ok_summary, f"[{name}] summary.json has total=3, done=1", f"summary.json = {result!r}")
        else:
            check(rc == 2, f"[{name}] exit 2 (failure is reported, not hidden)", f"exit {rc}")
            check(result == PREVIOUS, f"[{name}] previous summary.json left untouched", f"summary.json = {result!r}")
            check("Traceback" not in err and bool(err.strip()), f"[{name}] one clear error line on stderr, no traceback",
                  f"stderr: {err.strip()[:300]!r}")
        check(not stdout.strip() or should_succeed, f"[{name}] nothing misleading on stdout", f"stdout: {stdout.strip()[:120]!r}")
        check(not leftovers, f"[{name}] no temp files left behind", f"new files: {leftovers}")
    srv.shutdown()
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
