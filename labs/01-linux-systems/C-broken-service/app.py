#!/usr/bin/env python3
"""Lab 01-C demo app: config পড়ে, প্রতি ২ সেকেন্ডে heartbeat লেখে। কোনো network নেই।"""
import configparser
import sys
import time
from datetime import datetime, timezone

CONFIG = "/etc/lab-c/config.ini"

cfg = configparser.ConfigParser()
try:
    with open(CONFIG, encoding="utf-8") as f:   # না পড়তে পারলে স্পষ্ট error ও exit 1
        cfg.read_file(f)
except OSError as exc:
    print(f"ERROR cannot read config {CONFIG}: {exc}", flush=True)
    sys.exit(1)

path = cfg.get("app", "heartbeat_file", fallback="/srv/lab-c/data/heartbeat.log")
print(f"INFO started, writing heartbeat to {path}", flush=True)
while True:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(datetime.now(timezone.utc).isoformat() + " ok\n" + "x" * 2048 + "\n")
    except OSError as exc:
        print(f"ERROR heartbeat write failed: {exc}", flush=True)
        sys.exit(1)
    time.sleep(2)
