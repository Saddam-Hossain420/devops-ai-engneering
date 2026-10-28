#!/usr/bin/env python3
"""`ss -tan` সারাংশ — TCP state গণনা, listening port, এবং CLOSE_WAIT/TIME_WAIT সতর্কতা।

Input (read-only): ss -tan > ss.txt
Usage: python3 ss_summary.py ss.txt [--close-wait-warn 50] [--time-wait-warn 5000]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

STATE_HELP = {
    "LISTEN": "server অপেক্ষায়",
    "ESTAB": "চলমান connection",
    "SYN-SENT": "আমরা connect চেষ্টা করছি, উত্তর আসেনি (firewall/route?)",
    "SYN-RECV": "SYN পেয়েছি, handshake অসম্পূর্ণ (অনেক হলে SYN flood?)",
    "FIN-WAIT-1": "আমরা বন্ধ করছি", "FIN-WAIT-2": "আমরা বন্ধ করেছি, অন্য পক্ষের অপেক্ষা",
    "TIME-WAIT": "আমরা আগে বন্ধ করেছি; পুরোনো packet মোকাবেলায় কিছুক্ষণ অপেক্ষা",
    "CLOSE-WAIT": "অন্য পক্ষ বন্ধ করেছে, আমাদের app এখনো close() করেনি",
    "LAST-ACK": "আমরা শেষ ACK-এর অপেক্ষায়", "CLOSING": "দুই পক্ষ একসাথে বন্ধ করছে",
}


def split_addr(addr: str) -> tuple[str, str]:
    """'10.0.0.5:443', '[::1]:22', '*:80' → (host, port)."""
    host, _, port = addr.rpartition(":")
    return host.strip("[]"), port


def parse_ss(text: str) -> list[tuple[str, str, str]]:
    """(state, local, peer) — header বাদ।"""
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] in STATE_HELP:
            rows.append((parts[0], parts[3], parts[4]))
    return rows


def summarize(rows: list[tuple[str, str, str]], cw_warn: int, tw_warn: int) -> tuple[Counter, list[str], list[str]]:
    states = Counter(r[0] for r in rows)
    listening = sorted({split_addr(local)[1] for st, local, _ in rows if st == "LISTEN"}, key=lambda p: int(p))
    warnings = []
    if states["CLOSE-WAIT"] >= cw_warn:
        peers = Counter(split_addr(peer)[0] for st, _, peer in rows if st == "CLOSE-WAIT").most_common(3)
        warnings.append(f"{states['CLOSE-WAIT']} CLOSE-WAIT — application socket বন্ধ করছে না (leak); peers {peers}")
    if states["TIME-WAIT"] >= tw_warn:
        warnings.append(f"{states['TIME-WAIT']} TIME-WAIT — অনেক ছোট connection; keep-alive/pool ব্যবহার করুন")
    if states["SYN-SENT"]:
        peers = Counter(peer for st, _, peer in rows if st == "SYN-SENT").most_common(3)
        warnings.append(f"{states['SYN-SENT']} SYN-SENT — এই গন্তব্য উত্তর দিচ্ছে না: {peers}")
    return states, listening, warnings


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Summarize `ss -tan` output.")
    p.add_argument("file", type=Path)
    p.add_argument("--close-wait-warn", type=int, default=50)
    p.add_argument("--time-wait-warn", type=int, default=5000)
    args = p.parse_args(argv)
    try:
        rows = parse_ss(args.file.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 2
    states, listening, warnings = summarize(rows, args.close_wait_warn, args.time_wait_warn)
    for st, n in states.most_common():
        print(f"  {n:>6}  {st:11} {STATE_HELP[st]}")
    print(f"listening ports: {', '.join(listening) or '-'}")
    for w in warnings:
        print(f"WARN {w}")
    return 1 if warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
