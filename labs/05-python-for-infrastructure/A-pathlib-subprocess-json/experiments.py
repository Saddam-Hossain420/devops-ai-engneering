#!/usr/bin/env python3
"""Lab 05-A — pathlib, json ও subprocess-এর ১৫টি experiment। আগে README-তে নিজের অনুমান লিখুন, তারপর চালান।

  python3 experiments.py            # সব
  python3 experiments.py 4 7        # শুধু ৪ ও ৭ নম্বর

প্রতিটি experiment নিজের temp directory-তে কাজ করে; system-এ কিছু বদলায় না।
"""
from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

PY = sys.executable


def e1() -> object:
    return PurePosixPath("/srv/app") / "/etc/passwd"


def e2() -> object:
    p = PurePosixPath("backup-2026.tar.gz")
    return p.suffix, p.suffixes, p.stem


def e3() -> object:
    with tempfile.TemporaryDirectory() as d:
        for name in ("a.log", ".hidden.log", "b.txt"):
            Path(d, name).write_text("x")
        return sorted(p.name for p in Path(d).glob("*.log"))


def e4() -> object:
    return PurePosixPath("logs/../etc/./x.conf").parts


def e5() -> object:
    return json.loads('{"port": 8000, "port": 9000}')


def e6() -> object:
    return json.dumps({"ratio": float("nan")})


def e7() -> object:
    original = {1: "one"}
    return json.loads(json.dumps(original)), json.loads(json.dumps(original)) == original


def e8() -> object:
    return json.loads('{"replicas": 1e400}')


def e9() -> object:
    return json.dumps({"name": "ঢাকা"}), json.dumps({"name": "ঢাকা"}, ensure_ascii=False)


def e10() -> object:
    return isinstance(True, int), True + True, {1: "a", True: "b"}  # noqa: F601 — এটাই experiment


def e11() -> object:
    r = subprocess.run([PY, "-c", "import sys; sys.exit(3)"])
    return r.returncode


def e12() -> object:
    r = subprocess.run([PY, "-c", "import sys; print(sys.argv[1:])", "my file.txt", "*.log", "$HOME"],
                       capture_output=True, text=True)
    return r.stdout.strip()


def e13() -> object:
    return shlex.split("""tar czf "my backup.tgz" --exclude='*.tmp' /data"""), shlex.quote("it's")


def e14() -> object:
    r = subprocess.run([PY, "-c", "print('ok')"], capture_output=True)
    return r.stdout, r.stdout == "ok\n"


def e15() -> object:
    try:
        subprocess.run([PY, "-c", "import time; time.sleep(5)"], timeout=0.5)
    except subprocess.TimeoutExpired as exc:
        return f"TimeoutExpired after {exc.timeout}s"
    return "finished"


EXPERIMENTS = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11, e12, e13, e14, e15]


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    chosen = [int(a) for a in argv] or range(1, len(EXPERIMENTS) + 1)
    for n in chosen:
        fn = EXPERIMENTS[n - 1]
        try:
            result = repr(fn())
        except Exception as exc:                       # কিছু experiment-এর "উত্তর"-ই একটি exception
            result = f"{type(exc).__name__}: {exc}"
        print(f"{n:>2}. {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
