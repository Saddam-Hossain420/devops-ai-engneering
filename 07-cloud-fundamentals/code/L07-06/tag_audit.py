#!/usr/bin/env python3
"""tag_audit.py — cloud inventory (JSON export) থেকে tag-এর ঘাটতি ও cleanup-এর প্রার্থী খোঁজা। শুধু পড়ে, কিছু মোছে না।

  python3 tag_audit.py inventory.json --today 2026-10-28
  python3 tag_audit.py inventory.json --required owner,env,cost-center,expires --json

খোঁজে: প্রয়োজনীয় tag নেই · `expires` পেরিয়ে গেছে · কোনো instance-এ attached নয় এমন disk · কোনো কিছুতে যুক্ত নয় এমন
public IP · বন্ধ instance (compute বিল নেই, কিন্তু disk-এর বিল চলছে) · পুরোনো snapshot (--snapshot-days)।
Inventory-র রূপ: [{"id","type","state","tags":{…},"attached_to"?, "created"?, "size_gb"?}] — provider-এর CLI export থেকে বানানো।
Exit: 0 সব ঠিক, 1 কিছু পাওয়া গেছে, 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

DEFAULT_REQUIRED = ("owner", "env", "cost-center")


@dataclass
class Finding:
    id: str
    type: str
    kind: str
    detail: str


def audit(inventory: list[dict], today: date, required: tuple[str, ...], snapshot_days: int) -> list[Finding]:
    out: list[Finding] = []
    instances = {r["id"]: r for r in inventory if r["type"] == "instance"}
    for r in inventory:
        tags = {k.lower(): v for k, v in (r.get("tags") or {}).items()}
        missing = [t for t in required if not tags.get(t)]
        if missing:
            out.append(Finding(r["id"], r["type"], "missing-tags", ", ".join(missing)))
        if tags.get("expires"):
            try:
                expires = date.fromisoformat(tags["expires"])
            except ValueError:
                out.append(Finding(r["id"], r["type"], "bad-expires", f"expires={tags['expires']!r} is not YYYY-MM-DD"))
            else:
                if expires < today:
                    out.append(Finding(r["id"], r["type"], "expired",
                                       f"expired {(today - expires).days} day(s) ago (owner: {tags.get('owner', '?')})"))
        if r["type"] == "volume":
            parent = r.get("attached_to")
            if not parent:
                out.append(Finding(r["id"], "volume", "unattached-volume", f"{r.get('size_gb', '?')} GB billed, attached to nothing"))
            elif instances.get(parent, {}).get("state") == "stopped":
                out.append(Finding(r["id"], "volume", "stopped-instance-volume",
                                   f"{r.get('size_gb', '?')} GB still billed while {parent} is stopped"))
        if r["type"] == "public-ip" and not r.get("attached_to"):
            out.append(Finding(r["id"], "public-ip", "idle-public-ip", "allocated but not associated (often billed)"))
        if r["type"] == "snapshot" and r.get("created"):
            age = (today - date.fromisoformat(r["created"])).days
            if age > snapshot_days:
                out.append(Finding(r["id"], "snapshot", "old-snapshot", f"{age} days old ({r.get('size_gb', '?')} GB)"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Tag compliance and cleanup candidates (read-only).")
    ap.add_argument("inventory", type=Path)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--required", default=",".join(DEFAULT_REQUIRED))
    ap.add_argument("--snapshot-days", type=int, default=90)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        inventory = json.loads(a.inventory.read_text(encoding="utf-8"))
        findings = audit(inventory, a.today, tuple(t.strip().lower() for t in a.required.split(",") if t.strip()),
                         a.snapshot_days)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False))
    else:
        for f in findings:
            print(f"{f.kind:<24} {f.type:<10} {f.id:<24} {f.detail}")
        kinds: dict[str, int] = {}
        for f in findings:
            kinds[f.kind] = kinds.get(f.kind, 0) + 1
        print(f"{len(inventory)} resources, {len(findings)} finding(s): "
              + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
        print("nothing was changed — review with the owners, then clean up (dry-run first)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
