#!/usr/bin/env python3
"""demo_job.py — logsetup ব্যবহারের উদাহরণ: একটি কাল্পনিক backup job, একটি ব্যর্থতাসহ।

  python3 demo_job.py            # মানুষের পড়ার text (terminal)
  python3 demo_job.py --json     # এক লাইনে এক JSON (log collector-এর জন্য)
  python3 demo_job.py --json 2>&1 >/dev/null | jq -c 'select(.level=="error")'

সব data কৃত্রিম; কোনো আসল database বা secret নেই।
"""
from __future__ import annotations

import argparse
import contextvars
import logging
import sys
from concurrent.futures import ThreadPoolExecutor

from logsetup import request_context, request_id, setup_logging


def backup(db: str) -> int:
    log = logging.getLogger("ops.backup")          # "ops"-এর child — একই handler ব্যবহার করে
    if db == "billing":
        raise ConnectionError("could not connect to postgres://backup:s3cr3t-demo@10.0.0.5/billing")
    log.info("dumped %s", db, extra={"db": db, "size_mb": 120})
    return 120


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    log = setup_logging("info", json_output=args.json)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    with request_context("job-7f3a"):
        log.info("backup run started", extra={"dbs": ["orders", "billing"], "token": "demo-not-real"})
        log.debug("this is hidden at level info")
        failed = 0
        with ThreadPoolExecutor(max_workers=2) as pool:
            ctx = [contextvars.copy_context() for _ in range(2)]
            futures = {db: pool.submit(c.run, backup, db) for db, c in zip(["orders", "billing"], ctx, strict=True)}
            for db, fut in futures.items():
                try:
                    fut.result()
                except ConnectionError:
                    failed += 1
                    log.exception("backup failed", extra={"db": db})
        log.warning("password=hunter2 found in legacy config, please rotate")
        log.info("backup run finished", extra={"failed": failed, "request": request_id.get()})
    print(f"failed={failed}")                     # ফলাফল stdout-এ; log stderr-এ
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
