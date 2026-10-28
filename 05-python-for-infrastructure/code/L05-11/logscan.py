#!/usr/bin/env python3
"""logscan.py — nginx access log বিশ্লেষণ: error rate, latency percentile, শীর্ষ path/client, প্রতি মিনিটের সময়রেখা।

  python3 logscan.py /var/log/nginx/access.log /var/log/nginx/access.log.1.gz
  python3 logscan.py access.log --since 09:15 --until 09:30 --json
  zcat access.log.*.gz | python3 logscan.py -

Format: combined log + শেষে ঐচ্ছিক $request_time (সেকেন্ড)। File একবারে memory-তে নয় — লাইন ধরে পড়া; .gz নিজে চেনে।
"Spike" = যে মিনিটে 5xx-এর হার --spike-threshold-এর বেশি (কমপক্ষে --min-requests request থাকলে)।
Exit: 0 OK, 1 কোনো spike মিনিট পাওয়া গেছে, 2 input error।
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import TextIO

LINE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<method>[A-Z]+) (?P<path>(?:[^"\\]|\\.)*?) HTTP/[0-9.]+" '
    r'(?P<status>\d{3}) (?P<size>\d+|-)(?: "[^"]*" "[^"]*")?(?: (?P<rt>\d+(?:\.\d+)?))?\s*$')
TS_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


@dataclass
class Request:
    ip: str
    ts: datetime
    method: str
    path: str
    status: int
    size: int
    rt: float | None


@dataclass
class Stats:
    total: int = 0
    unparsed: int = 0
    status: Counter[str] = field(default_factory=Counter)
    paths: Counter[str] = field(default_factory=Counter)
    paths_5xx: Counter[str] = field(default_factory=Counter)
    ips: Counter[str] = field(default_factory=Counter)
    latencies: list[float] = field(default_factory=list)
    per_minute: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))
    bytes: int = 0
    first: datetime | None = None
    last: datetime | None = None


def parse(line: str) -> Request | None:
    m = LINE.match(line)
    if not m:
        return None
    try:
        ts = datetime.strptime(m["ts"], TS_FORMAT)
    except ValueError:
        return None
    path = m["path"].split("?", 1)[0]                     # query string বাদ — নইলে প্রতিটি URL আলাদা গোনা হয়
    return Request(m["ip"], ts, m["method"], path, int(m["status"]),
                   0 if m["size"] == "-" else int(m["size"]), float(m["rt"]) if m["rt"] else None)


def open_any(name: str) -> TextIO:
    if name == "-":
        return io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
    path = Path(name)
    with path.open("rb") as f:
        magic = f.read(2)
    if magic == b"\x1f\x8b":                              # নামে নয়, বিষয়বস্তু দেখে gzip চেনা
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def lines_from(names: Iterable[str]) -> Iterator[str]:
    for name in names:
        with open_any(name) as f:
            yield from f


def percentile(sorted_values: list[float], p: float) -> float | None:
    """Nearest-rank: সবসময় একটি আসল পরিমাপ ফেরত দেয় (interpolation করে বানানো মান নয়)।"""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(p / 100 * len(sorted_values)))
    return sorted_values[rank - 1]


def analyze(lines: Iterable[str], since: time | None = None, until: time | None = None) -> Stats:
    s = Stats()
    for line in lines:
        if not line.strip():
            continue
        req = parse(line)
        if req is None:
            s.unparsed += 1
            continue
        t = req.ts.time()
        if (since and t < since) or (until and t >= until):
            continue
        s.total += 1
        klass = f"{req.status // 100}xx"
        s.status[klass] += 1
        s.paths[req.path] += 1
        s.ips[req.ip] += 1
        s.bytes += req.size
        if req.status >= 500:
            s.paths_5xx[req.path] += 1
        if req.rt is not None:
            s.latencies.append(req.rt)
        bucket = s.per_minute[req.ts.strftime("%H:%M")]
        bucket[0] += 1
        bucket[1] += req.status >= 500
        s.first = req.ts if s.first is None or req.ts < s.first else s.first
        s.last = req.ts if s.last is None or req.ts > s.last else s.last
    s.latencies.sort()
    return s


def spikes(s: Stats, threshold: float, min_requests: int) -> list[tuple[str, int, int]]:
    return [(minute, total, errors) for minute, (total, errors) in sorted(s.per_minute.items())
            if total >= min_requests and errors / total > threshold]


def report(s: Stats, top: int, threshold: float, min_requests: int) -> dict[str, object]:
    err = s.status.get("5xx", 0)
    return {
        "window": [s.first.isoformat() if s.first else None, s.last.isoformat() if s.last else None],
        "requests": s.total,
        "unparsed_lines": s.unparsed,
        "status": dict(sorted(s.status.items())),
        "error_rate_5xx": round(err / s.total, 4) if s.total else None,
        "latency_s": {f"p{p}": percentile(s.latencies, p) for p in (50, 90, 99)}
                     | {"max": s.latencies[-1] if s.latencies else None, "samples": len(s.latencies)},
        "top_paths": s.paths.most_common(top),
        "top_5xx_paths": s.paths_5xx.most_common(top),
        "top_clients": s.ips.most_common(top),
        "spike_minutes": [{"minute": m, "requests": t, "errors_5xx": e} for m, t, e in spikes(s, threshold, min_requests)],
    }


def hhmm(text: str) -> time:
    try:
        return time.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected HH:MM, got {text!r}") from None


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Summarise nginx access logs.")
    ap.add_argument("files", nargs="+", help="log files (.gz ok) or - for stdin")
    ap.add_argument("--since", type=hhmm)
    ap.add_argument("--until", type=hhmm)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--spike-threshold", type=float, default=0.05, help="5xx share per minute (default 0.05)")
    ap.add_argument("--min-requests", type=int, default=20)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    try:
        stats = analyze(lines_from(args.files), args.since, args.until)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rep = report(stats, args.top, args.spike_threshold, args.min_requests)
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        lat = rep["latency_s"]
        print(f"window      {rep['window'][0]} → {rep['window'][1]}")
        print(f"requests    {rep['requests']}  (unparsed lines: {rep['unparsed_lines']})")
        print(f"status      {rep['status']}   5xx rate: {rep['error_rate_5xx']}")
        print(f"latency     p50={lat['p50']}s p90={lat['p90']}s p99={lat['p99']}s max={lat['max']}s")
        for title, key in (("top paths", "top_paths"), ("top 5xx", "top_5xx_paths"), ("top clients", "top_clients")):
            print(f"{title:<11} " + ", ".join(f"{k} ({v})" for k, v in rep[key]))
        for sp in rep["spike_minutes"]:
            print(f"SPIKE       {sp['minute']}  {sp['errors_5xx']}/{sp['requests']} requests 5xx")
    if stats.unparsed and stats.total == 0:
        print("warning: no line matched the expected format", file=sys.stderr)
    return 1 if rep["spike_minutes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
