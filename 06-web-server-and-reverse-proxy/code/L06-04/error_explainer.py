#!/usr/bin/env python3
"""error_explainer.py — nginx error.log-এর লাইন থেকে client কোন status দেখেছে ও সম্ভাব্য কারণ কী, তা বলে।

  python3 error_explainer.py /var/log/nginx/error.log
  python3 error_explainer.py sample-error.log --summary
  sudo tail -f /var/log/nginx/error.log | python3 error_explainer.py -

চেনে (nginx-এর বার্তার রূপ অনুযায়ী): connection refused, timeout (connect/read), upstream মাঝপথে বন্ধ,
no live upstreams, permission denied (socket/SELinux), body খুব বড়, open-file সীমা, resolver ব্যর্থতা।
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

PATTERNS: list[tuple[str, str, str, str]] = [
    # (regex, status, কারণ, প্রথম পদক্ষেপ)
    (r"connect\(\) failed \(111: Connection refused\) while connecting to upstream", "502",
     "upstream process is not listening (down, crashed, wrong port, or bound to another address)",
     "systemctl status <app>; ss -ltnp 'sport = :PORT'; compare with proxy_pass"),
    (r"connect\(\) to unix:\S+ failed \(2: No such file or directory\)", "502",
     "unix socket file does not exist (app not running, or different path)",
     "ls -l the socket path; check the app's bind/RuntimeDirectory"),
    (r"connect\(\) to unix:\S+ failed \(13: Permission denied\)", "502",
     "nginx worker (www-data) cannot open the unix socket — socket/directory permissions",
     "namei -l <socket>; give group www-data rw on the socket (L06-05)"),
    (r"\(13: Permission denied\) while connecting to upstream", "502",
     "connect blocked — on Fedora/RHEL usually SELinux (httpd_can_network_connect)",
     "ausearch -m avc -ts recent; setsebool -P httpd_can_network_connect 1"),
    (r"upstream timed out \(110: Connection timed out\) while connecting to upstream", "504",
     "TCP connect to upstream did not complete (firewall drop, wrong IP, host down)",
     "check proxy_connect_timeout, route/firewall to upstream (L02-16)"),
    (r"upstream timed out \(110: Connection timed out\) while reading response header from upstream", "504",
     "app accepted the request but answered slower than proxy_read_timeout",
     "app logs/latency for that request id; slow query? raise timeout only if justified"),
    (r"upstream prematurely closed connection while reading response header from upstream", "502",
     "app closed the connection without a response — crash, worker killed (OOM), or protocol mismatch",
     "app logs around the time; dmesg for OOM (L01-09); http vs https upstream"),
    (r"recv\(\) failed \(104: Connection reset by peer\) while reading response header from upstream", "502",
     "app reset the connection — crash/restart, or keepalive connection closed by the app",
     "app restarts? keepalive_timeout of the app shorter than nginx's reuse?"),
    (r"no live upstreams while connecting to upstream", "502",
     "every server in the upstream block is marked failed (max_fails reached)",
     "find the first failure above this line; fix the upstream, then it recovers after fail_timeout"),
    (r"client intended to send too large body", "413",
     "request body larger than client_max_body_size",
     "raise client_max_body_size for that location only, if the size is legitimate"),
    (r"\(24: Too many open files\)", "500/502",
     "worker hit its open-file limit",
     "worker_rlimit_nofile / LimitNOFILE (L06-02)"),
    (r"could not be resolved|no resolver defined to resolve", "502",
     "upstream hostname could not be resolved at runtime",
     "use an IP/upstream block, or configure 'resolver' when proxy_pass uses variables"),
    (r"SSL_do_handshake\(\) failed .* while SSL handshaking to upstream", "502",
     "TLS to upstream failed (http vs https, SNI, certificate)",
     "proxy_ssl_server_name on; check upstream scheme"),
]
COMPILED = [(re.compile(p), s, c, a) for p, s, c, a in PATTERNS]
HEAD = re.compile(r"^(?P<ts>\d{4}/\d\d/\d\d \d\d:\d\d:\d\d) \[(?P<level>\w+)\] \d+#\d+: (?:\*\d+ )?(?P<msg>.*)$")
FIELD = re.compile(r'(\w+): "?([^",]*)"?')


@dataclass
class Explained:
    ts: str
    status: str
    cause: str
    action: str
    request: str
    upstream: str


def explain(line: str) -> Explained | None:
    m = HEAD.match(line.strip())
    msg = m.group("msg") if m else line
    for rx, status, cause, action in COMPILED:
        if rx.search(msg):
            fields = dict(FIELD.findall(msg.split(", ", 1)[1] if ", " in msg else ""))
            return Explained(m.group("ts") if m else "-", status, cause, action,
                             fields.get("request", "-"), fields.get("upstream", "-"))
    return None


def lines_from(name: str) -> Iterable[str]:
    if name == "-":
        yield from sys.stdin
    else:
        with open(name, encoding="utf-8", errors="replace") as f:
            yield from f


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Explain nginx error.log lines.")
    ap.add_argument("logfile")
    ap.add_argument("--summary", action="store_true", help="only counts per cause")
    a = ap.parse_args(argv)
    counts: Counter[tuple[str, str]] = Counter()
    unknown = 0
    try:
        for line in lines_from(a.logfile):
            if not line.strip():
                continue
            e = explain(line)
            if e is None:
                unknown += 1
                continue
            counts[(e.status, e.cause)] += 1
            if not a.summary:
                print(f"{e.ts}  {e.status:<7} {e.request}\n    cause:  {e.cause}\n    upstream: {e.upstream}\n"
                      f"    next:   {e.action}")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("\nsummary:")
    for (status, cause), n in counts.most_common():
        print(f"  {n:>4} × {status:<7} {cause}")
    print(f"  {unknown:>4} × (not recognised)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
