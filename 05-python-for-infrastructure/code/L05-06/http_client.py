#!/usr/bin/env python3
"""http_client.py — stdlib (urllib) দিয়ে নির্ভরযোগ্য HTTP call: timeout, সীমিত retry, exponential backoff + jitter,
Retry-After মানা, এবং শুধু নিরাপদ (idempotent) request-এ retry।

  python3 http_client.py http://127.0.0.1:8099/flaky --retries 4
  python3 http_client.py http://127.0.0.1:8099/health --json

Retry হয়: connection error, timeout, 429, 502, 503, 504 — শুধু GET/HEAD/PUT/DELETE/OPTIONS-এ
(POST-এ শুধু idempotency_key থাকলে)। 4xx (429 ছাড়া) কখনো retry নয় — আবার পাঠালেও একই ফল।
Exit: 0 2xx, 1 HTTP error, 2 network/timeout (সব চেষ্টা শেষে)।
"""
from __future__ import annotations

import argparse
import email.utils
import json
import random
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

RETRY_STATUS = frozenset({429, 502, 503, 504})
IDEMPOTENT = frozenset({"GET", "HEAD", "PUT", "DELETE", "OPTIONS"})
USER_AGENT = "devops-ai-engineering-http-client/1.0"


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    body: bytes
    attempts: int
    elapsed_s: float
    history: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8"))


class RequestFailedError(Exception):
    """সব চেষ্টা শেষে network/timeout ব্যর্থতা (HTTP response পাওয়া যায়নি)।"""

    def __init__(self, message: str, attempts: int, history: list[str]) -> None:
        super().__init__(message)
        self.attempts, self.history = attempts, history


def backoff_delay(attempt: int, base: float, cap: float, rng: Callable[[], float] = random.random) -> float:
    """Full jitter: 0 থেকে min(cap, base * 2**attempt)-এর মধ্যে random — সব client একসাথে ফেরত আসে না।"""
    return rng() * min(cap, base * (2 ** attempt))


def retry_after_seconds(value: str | None, now: float | None = None) -> float | None:
    """Retry-After: সেকেন্ড ("5") অথবা HTTP তারিখ — দুটোই বৈধ (RFC 9110)।"""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        when = email.utils.parsedate_to_datetime(value).timestamp()
    except (TypeError, ValueError):
        return None
    return max(0.0, when - (now if now is not None else time.time()))


def request(url: str, *, method: str = "GET", body: bytes | None = None,
            headers: Mapping[str, str] | None = None, timeout: float = 5.0, retries: int = 3,
            backoff_base: float = 0.5, backoff_cap: float = 10.0, max_retry_after: float = 30.0,
            idempotency_key: str | None = None, sleep: Callable[[float], None] = time.sleep) -> Response:
    method = method.upper()
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    if idempotency_key:
        hdrs["Idempotency-Key"] = idempotency_key
    may_retry = method in IDEMPOTENT or idempotency_key is not None
    attempts_allowed = 1 + (retries if may_retry else 0)
    history: list[str] = []
    start = time.monotonic()

    for attempt in range(attempts_allowed):
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        delay: float | None = None
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return Response(resp.status, dict(resp.headers), resp.read(), attempt + 1,
                                round(time.monotonic() - start, 3), history)
        except urllib.error.HTTPError as exc:                # 4xx/5xx — response আছে
            with exc:                                        # বন্ধ না করলে connection leak (ResourceWarning)
                payload = exc.read()
            if exc.code not in RETRY_STATUS or attempt == attempts_allowed - 1:
                return Response(exc.code, dict(exc.headers), payload, attempt + 1,
                                round(time.monotonic() - start, 3), history)
            history.append(f"attempt {attempt + 1}: HTTP {exc.code}")
            delay = retry_after_seconds(exc.headers.get("Retry-After"))
            if delay is not None and delay > max_retry_after:
                return Response(exc.code, dict(exc.headers), payload, attempt + 1,
                                round(time.monotonic() - start, 3), history)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            history.append(f"attempt {attempt + 1}: {type(reason).__name__}: {reason}")
            if attempt == attempts_allowed - 1:
                raise RequestFailedError(f"{method} {url} failed after {attempt + 1} attempt(s): {reason}",
                                    attempt + 1, history) from None
        if delay is None:
            delay = backoff_delay(attempt, backoff_base, backoff_cap)
        history[-1] += f", retry in {delay:.2f}s"
        sleep(delay)
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="HTTP request with timeout and safe retries.")
    ap.add_argument("url")
    ap.add_argument("-X", "--method", default="GET")
    ap.add_argument("--timeout", type=float, default=5.0)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--json", action="store_true", help="print a JSON summary")
    args = ap.parse_args(argv)
    try:
        r = request(args.url, method=args.method, timeout=args.timeout, retries=args.retries)
    except RequestFailedError as exc:
        for h in exc.history:
            print(f"  {h}", file=sys.stderr)
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for h in r.history:
        print(f"  {h}", file=sys.stderr)
    if args.json:
        print(json.dumps({"status": r.status, "attempts": r.attempts, "elapsed_s": r.elapsed_s,
                          "body": r.body.decode("utf-8", "replace")[:500]}, indent=2))
    else:
        print(f"HTTP {r.status} after {r.attempts} attempt(s) in {r.elapsed_s}s")
        print(r.body.decode("utf-8", "replace")[:500])
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
