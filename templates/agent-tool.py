"""Template: AI agent-এর জন্য নিরাপদ read-only tool.

নিয়ম:
1. Allowlist — শুধু অনুমোদিত path/resource।
2. Read-only — কোনো write/delete নয়।
3. Output সীমিত — বড় log পুরো পাঠানো নয়।
4. Tool output = untrusted data। এর ভেতরের "নির্দেশ" কখনো মানা হবে না।
5. প্রতিটি call audit log-এ।
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ALLOWED_LOG_DIR = Path("/var/log/app").resolve()  # environment অনুযায়ী বদলান
MAX_LINES = 200
AUDIT_LOG = Path("agent-audit.jsonl")


def _audit(tool: str, args: dict, ok: bool, note: str = "") -> None:
    entry = {"ts": time.time(), "tool": tool, "args": args, "ok": ok, "note": note}
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_log_tail(filename: str, lines: int = 50) -> dict:
    """অনুমোদিত directory থেকে log-এর শেষ অংশ পড়ে (read-only)."""
    args = {"filename": filename, "lines": lines}
    target = (ALLOWED_LOG_DIR / filename).resolve()
    if ALLOWED_LOG_DIR not in target.parents:  # path traversal (../../etc/shadow) আটকানো
        _audit("read_log_tail", args, False, "outside allowlist")
        return {"error": "path not allowed"}
    if not target.is_file():
        _audit("read_log_tail", args, False, "not found")
        return {"error": "not found"}
    n = max(1, min(lines, MAX_LINES))
    tail = target.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    _audit("read_log_tail", args, True)
    # data হিসেবে চিহ্নিত — model যেন এটিকে নির্দেশ হিসেবে না নেয়
    return {"untrusted_content": tail, "source": str(target), "lines": len(tail)}
