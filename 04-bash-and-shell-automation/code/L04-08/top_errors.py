#!/usr/bin/env python3
"""top_errors.py — access log-এ 5xx error সবচেয়ে বেশি এমন path, JSON-এ।  (Python সংস্করণ)

  python3 top_errors.py access.log [N]

Regex দিয়ে পুরো লাইন parse (quote-এর ভেতরের space/escaped quote ঠিকভাবে), json module দিয়ে নিরাপদ output,
অসম্পূর্ণ লাইন গণনা করে বাদ। Exit: 0 OK, 2 input error।
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

# "METHOD PATH PROTO" — PATH-এর ভেতরে escaped quote (\") থাকতে পারে
# শেষের "HTTP/x"-এ নোঙর — প্রথম সংস্করণে lazy match `"/my file.txt"`-কে "/my" কেটেছিল (আসলে ঘটেছিল)
LINE = re.compile(r'^\S+ \S+ \S+ \[[^\]]+\] "(?:[A-Z]+) ((?:[^"\\]|\\.)*) HTTP/[0-9.]+" (\d{3}) ')


def top_errors(lines, n: int = 5) -> dict:
    counts: Counter[str] = Counter()
    skipped = 0
    for raw in lines:
        m = LINE.match(raw)
        if not m:
            skipped += raw.strip() != ""
            continue
        path, status = m.group(1), m.group(2)
        if status.startswith("5"):
            counts[path.replace('\\"', '"').replace("\\\\", "\\")] += 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]
    return {"top": [{"path": p, "count": c} for p, c in top], "total_5xx": sum(counts.values()),
            "unparsed_lines": skipped}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or len(argv) > 2 or (len(argv) == 2 and not argv[1].isdigit()):
        print("usage: top_errors.py LOGFILE [N]", file=sys.stderr)
        return 2
    try:
        with open(argv[0], encoding="utf-8", errors="replace") as f:
            result = top_errors(f, int(argv[1]) if len(argv) == 2 else 5)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
