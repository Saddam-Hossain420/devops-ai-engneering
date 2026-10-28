#!/usr/bin/env python3
"""Lab 05-B verification — আপনার taskflow_report.py-কে চারটি পরিস্থিতিতে চালিয়ে সঠিক উত্তরের সাথে মেলায়।

  python3 check_b.py path/to/taskflow_report.py          exit 0 = ALL CHECKS PASSED

সঠিক উত্তর এই script নিজে হিসাব করে (gen_taskflow_log.py-এর output থেকে) — কোনো স্থির সংখ্যা মুখস্থ নেই।
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ID = re.compile(r"^/tasks/\d+$")


def nearest_rank(values: list[float], p: float) -> float:
    values = sorted(values)
    return values[max(1, math.ceil(p / 100 * len(values))) - 1]


def truth(text: str) -> dict[str, object]:
    reqs, unparsed = [], 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            unparsed += 1
            continue
        if doc.get("msg") == "request":
            reqs.append(doc)
    routes: dict[str, list[dict[str, object]]] = {}
    for r in reqs:
        path = "/tasks/{id}" if ID.match(str(r["path"])) else r["path"]
        routes.setdefault(f"{r['method']} {path}", []).append(r)
    errors = sum(1 for r in reqs if int(r["status"]) >= 500)
    return {
        "requests": len(reqs),
        "unparsed": unparsed,
        "error_rate_5xx": round(errors / len(reqs), 4) if reqs else None,
        "by_route": {k: {"count": len(v),
                         "p50_ms": nearest_rank([float(x["duration_ms"]) for x in v], 50),
                         "p99_ms": nearest_rank([float(x["duration_ms"]) for x in v], 99),
                         "errors_5xx": sum(1 for x in v if int(x["status"]) >= 500)}
                     for k, v in sorted(routes.items())},
        "slowest_request_ids": [r["request_id"] for r in sorted(reqs, key=lambda r: -float(r["duration_ms"]))[:3]],
    }


def run(tool: Path, args: list[str], stdin: str | None = None) -> tuple[int, object, str]:
    proc = subprocess.run([sys.executable, str(tool), *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", timeout=120)
    try:
        doc = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError:
        doc = "NOT JSON: " + proc.stdout[:200]
    return proc.returncode, doc, proc.stderr


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):                 # Windows pipe-এ cp1252 — বাংলা/→ লিখতে UTF-8
            stream.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2 or not Path(sys.argv[1]).is_file():
        print("usage: python3 check_b.py path/to/taskflow_report.py", file=sys.stderr)
        return 2
    tool = Path(sys.argv[1]).resolve()
    failed = 0

    def report(ok: bool, name: str, detail: str = "") -> None:
        nonlocal failed
        print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n      {detail}"))
        failed += not ok

    with tempfile.TemporaryDirectory() as d:
        log = Path(d, "taskflow-access.jsonl")
        log.write_text(subprocess.run([sys.executable, str(HERE / "gen_taskflow_log.py"), "--lines", "5000"],
                                      capture_output=True, text=True, check=True).stdout, encoding="utf-8")
        want = truth(log.read_text(encoding="utf-8"))

        # ১. পুরো report — প্রতিটি field আলাদা যাচাই, যাতে কোনটা ভুল বোঝা যায়
        rc, got, err = run(tool, ["--json", str(log), "--max-error-rate", "0.5"])
        if not isinstance(got, dict):
            report(False, "report is a JSON object on stdout", f"got {got!r}; stderr: {err[:300]}")
        else:
            for key in ("requests", "unparsed", "error_rate_5xx", "slowest_request_ids"):
                report(got.get(key) == want[key], f"{key}", f"expected {want[key]!r}, got {got.get(key)!r}")
            got_routes = got.get("by_route", {})
            report(set(got_routes) == set(want["by_route"]), "by_route keys (paths normalised to /tasks/{id})",
                   f"expected {sorted(want['by_route'])}, got {sorted(got_routes)}")
            for route, stats in want["by_route"].items():
                g = got_routes.get(route, {})
                bad = {k: (v, g.get(k)) for k, v in stats.items() if g.get(k) != v}
                report(not bad, f"by_route[{route!r}]", f"(expected, got): {bad}")
            report(rc == 0, "exit 0 when error rate is below --max-error-rate", f"exit {rc}")

        # ২. threshold পেরোলে exit 1
        rc, _, _ = run(tool, ["--json", str(log), "--max-error-rate", "0.001"])
        report(rc == 1, "exit 1 when error rate exceeds --max-error-rate", f"exit {rc}")

        # ৩. stdin থেকে (`-`) একই ফল
        rc, got, err = run(tool, ["--json", "-"], stdin=log.read_text(encoding="utf-8"))
        report(isinstance(got, dict) and got.get("requests") == want["requests"], "reads stdin with '-'",
               f"exit {rc}, got {str(got)[:120]!r}, stderr {err[:200]!r}")

        # ৪. খালি input — crash নয়
        empty = Path(d, "empty.jsonl")
        empty.write_text("", encoding="utf-8")
        rc, got, err = run(tool, ["--json", str(empty)])
        report(rc == 0 and isinstance(got, dict) and got.get("requests") == 0 and got.get("error_rate_5xx") is None,
               "empty input → requests 0, error_rate_5xx null, exit 0", f"exit {rc}, got {got!r}, stderr {err[:200]!r}")

        # ৫. অস্তিত্বহীন file → exit 2, traceback নয়
        rc, _, err = run(tool, ["--json", str(Path(d, "missing.jsonl"))])
        report(rc == 2 and "Traceback" not in err, "missing file → exit 2 without traceback", f"exit {rc}, stderr {err[:200]!r}")

    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
