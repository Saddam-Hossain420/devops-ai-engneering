#!/usr/bin/env python3
"""Lab 05-C — একটি ফাঁদযুক্ত API sync tool তৈরি করে, নিজের directory-তে। System বা global কিছু বদলায় না।

  python3 break_it.py ~/lab05c
"""
from __future__ import annotations

import sys
from pathlib import Path

SYNC = '''#!/usr/bin/env python3
"""sync.py — TaskFlow API থেকে task-এর সারাংশ এনে একটি JSON file-এ লেখে (dashboard এই file পড়ে)।

  python3 sync.py http://127.0.0.1:8000 summary.json

Spec: সফল হলে exit 0 ও summary.json = {"total": N, "done": D, "fetched_at": "..."}।
      ব্যর্থ হলে exit 2, stderr-এ এক লাইনের কারণ, এবং আগের summary.json অক্ষত।
      ১০ সেকেন্ডের বেশি কখনো নয়; সাময়িক 503/502-এ কয়েকবার চেষ্টা।
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone


def main():
    base, out = sys.argv[1], sys.argv[2]
    with open(out, "w") as f:
        try:
            body = urllib.request.urlopen(base + "/tasks?limit=100").read()
            tasks = json.loads(body)["items"]
            summary = {
                "total": len(tasks),
                "done": sum(1 for t in tasks if t["done"]),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            json.dump(summary, f)
            print("synced", summary["total"], "tasks")
        except Exception as exc:
            print("sync failed:", exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python3 break_it.py DIR", file=sys.stderr)
        return 64
    dest = Path(sys.argv[1]).expanduser()
    if dest.exists():
        print(f"refusing: {dest} already exists (reset.py দিয়ে মুছুন)", file=sys.stderr)
        return 2
    dest.mkdir(parents=True)
    (dest / ".lab05c").write_text("Lab 05-C working directory\n", encoding="utf-8")
    (dest / "sync.py").write_text(SYNC, encoding="utf-8")
    print(f"created {dest / 'sync.py'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
