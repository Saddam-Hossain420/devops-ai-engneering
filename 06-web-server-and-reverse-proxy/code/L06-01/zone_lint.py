#!/usr/bin/env python3
"""zone_lint.py — DNS zone file (BIND format-এর সরল অংশ) পড়ে সাধারণ ভুল ধরে; TTL পরিবর্তনের সময়রেখা হিসাব করে।

  python3 zone_lint.py example-zone.txt
  python3 zone_lint.py example-zone.txt --json
  python3 zone_lint.py plan --old-ttl 86400 --new-ttl 300 --change-at 2026-11-03T02:00Z

সমর্থিত: $ORIGIN, $TTL, `@`, relative/absolute নাম, প্রথম column খালি = আগের নাম, A AAAA CNAME MX NS TXT CAA SOA SRV।
(multi-line SOA-র `( … )` এক লাইনে জোড়া হয়; quoted TXT-এ ';' comment নয়।)
Exit: 0 কোনো error নেই, 1 error আছে, 2 file/argument error।
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import re
import shlex
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

TYPES = {"A", "AAAA", "CNAME", "MX", "NS", "TXT", "CAA", "SOA", "SRV", "PTR"}
CLASSES = {"IN"}
INTERNAL_NETS = [ipaddress.IPv4Network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10")]


@dataclass(frozen=True)
class Record:
    line: int
    name: str          # সবসময় absolute, শেষে '.'
    ttl: int
    type: str
    rdata: tuple[str, ...]


@dataclass(frozen=True)
class Finding:
    level: str         # error / warning
    line: int
    code: str
    message: str


def strip_comment(line: str) -> str:
    out, quoted = [], False
    for ch in line:
        if ch == '"':
            quoted = not quoted
        if ch == ";" and not quoted:
            break
        out.append(ch)
    return "".join(out).rstrip()


def absolute(name: str, origin: str) -> str:
    if name == "@":
        return origin
    return name.lower() if name.endswith(".") else f"{name}.{origin}".lower()


def parse_ttl(token: str) -> int | None:
    m = re.fullmatch(r"(?i)(\d+)([smhdw]?)", token)
    if not m:
        return None
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[m.group(2).lower()]


def logical_lines(text: str) -> list[tuple[int, str]]:
    """`( … )` জুড়ে থাকা লাইন এক করে; প্রতিটির শুরুর লাইন নম্বর রাখে।"""
    out, buf, start, depth = [], "", 0, 0
    for n, raw in enumerate(text.splitlines(), 1):
        line = strip_comment(raw)
        if not buf:
            start = n
        depth += line.count("(") - line.count(")")
        buf += (" " if buf else "") + line.replace("(", " ").replace(")", " ") if buf else line.replace("(", " ").replace(")", " ")
        if depth <= 0:
            if buf.strip():
                out.append((start, buf))
            buf, depth = "", 0
    return out


def parse(text: str, origin: str = ".") -> tuple[list[Record], list[Finding]]:
    records: list[Record] = []
    findings: list[Finding] = []
    default_ttl: int | None = None
    last_name: str | None = None
    for n, line in logical_lines(text):
        if line.startswith("$ORIGIN"):
            origin = line.split()[1].lower()
            if not origin.endswith("."):
                findings.append(Finding("error", n, "origin-not-absolute", f"$ORIGIN {origin} must end with '.'"))
                origin += "."
            continue
        if line.startswith("$TTL"):
            default_ttl = parse_ttl(line.split()[1])
            continue
        try:
            tokens = shlex.split(line, posix=True)
        except ValueError:
            findings.append(Finding("error", n, "syntax", "unbalanced quotes"))
            continue
        if line[0].isspace():
            if last_name is None:
                findings.append(Finding("error", n, "no-owner", "record without an owner name"))
                continue
            name = last_name
        else:
            name = absolute(tokens.pop(0), origin)
        ttl = None
        while tokens and tokens[0].upper() not in TYPES:
            tok = tokens.pop(0)
            if tok.upper() in CLASSES:
                continue
            ttl = parse_ttl(tok)
            if ttl is None:
                findings.append(Finding("error", n, "syntax", f"unexpected token {tok!r}"))
                break
        if not tokens:
            findings.append(Finding("error", n, "syntax", "missing record type"))
            continue
        rtype = tokens.pop(0).upper()
        effective = ttl if ttl is not None else default_ttl
        if effective is None:
            findings.append(Finding("error", n, "no-ttl", "no TTL and no $TTL default"))
            effective = 0
        records.append(Record(n, name, effective, rtype, tuple(tokens)))
        last_name = name
    return records, findings


def target_of(r: Record) -> str | None:
    if r.type in ("CNAME", "NS", "PTR"):
        return r.rdata[0] if r.rdata else None
    if r.type == "MX":
        return r.rdata[1] if len(r.rdata) > 1 else None
    if r.type == "SRV":
        return r.rdata[3] if len(r.rdata) > 3 else None
    return None


def lint(records: list[Record], zone: str) -> list[Finding]:
    out: list[Finding] = []
    by_name: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        by_name[r.name].append(r)
    cnames = {r.name for r in records if r.type == "CNAME"}

    for r in records:
        if r.type == "A":
            try:
                ip = ipaddress.IPv4Address(r.rdata[0])
            except (ValueError, IndexError):
                out.append(Finding("error", r.line, "bad-a", f"{r.name} A {' '.join(r.rdata)} is not an IPv4 address"))
                continue
            # ip.is_private নয়: সেটা documentation range (192.0.2.0/24)-কেও "private" বলে — RFC 1918 ≠ is_private
            if ip.is_loopback or ip.is_link_local or any(ip in net for net in INTERNAL_NETS):
                out.append(Finding("warning", r.line, "private-ip", f"{r.name} → {ip} is private/loopback in a public zone"))
        elif r.type == "AAAA":
            try:
                ipaddress.IPv6Address(r.rdata[0])
            except (ValueError, IndexError):
                out.append(Finding("error", r.line, "bad-aaaa", f"{r.name} AAAA {' '.join(r.rdata)} is not IPv6"))
        tgt = target_of(r)
        if tgt and not tgt.endswith(".") and zone.rstrip(".") in tgt:
            out.append(Finding("error", r.line, "missing-trailing-dot",
                               f"{r.type} target {tgt!r} has no trailing dot → becomes {tgt}.{zone}"))
        if r.type in ("MX", "NS", "SRV") and tgt and tgt.endswith(".") and tgt.lower() in cnames:
            out.append(Finding("error", r.line, "target-is-cname", f"{r.type} target {tgt} is a CNAME (RFC 2181 §10.3)"))
        if r.ttl and r.ttl < 60:
            out.append(Finding("warning", r.line, "ttl-very-low", f"{r.name} {r.type} TTL {r.ttl}s — resolver load, some ignore it"))

    for name, recs in by_name.items():
        types = {r.type for r in recs}
        if "CNAME" in types:
            first = min(r.line for r in recs if r.type == "CNAME")
            if name == zone:
                out.append(Finding("error", first, "cname-at-apex", f"CNAME at zone apex {name} (conflicts with SOA/NS) — use A/AAAA or provider ALIAS"))
            elif len(recs) > 1:
                others = sorted(types - {"CNAME"}) or ["CNAME"]
                out.append(Finding("error", first, "cname-and-other-data", f"{name} has CNAME plus {', '.join(others)} (RFC 1034 §3.6.2)"))
        spf = [r for r in recs if r.type == "TXT" and r.rdata and "".join(r.rdata).lower().startswith("v=spf1")]
        if len(spf) > 1:
            out.append(Finding("error", spf[1].line, "multiple-spf", f"{name} has {len(spf)} SPF records — SPF permerror (RFC 7208 §3.2)"))
        a_ttls = {r.ttl for r in recs if r.type in ("A", "AAAA")}
        if len(a_ttls) > 1:
            out.append(Finding("warning", min(r.line for r in recs), "mixed-ttl", f"{name} A/AAAA records have different TTLs {sorted(a_ttls)}"))

    if not any(r.type == "CAA" and r.name == zone for r in records):
        out.append(Finding("warning", 0, "no-caa", f"no CAA at {zone} — any CA may issue certificates (RFC 8659)"))
    if not any(r.type == "NS" and r.name == zone for r in records):
        out.append(Finding("error", 0, "no-ns", f"no NS records at apex {zone}"))
    return sorted(out, key=lambda f: (f.line, f.code))


def plan(old_ttl: int, new_ttl: int, change_at: datetime) -> list[tuple[datetime, str]]:
    """TTL কমিয়ে নিরাপদ migration: পুরোনো TTL শেষ হওয়ার আগেই কম TTL ছড়িয়ে পড়তে হবে।"""
    lower_by = change_at - timedelta(seconds=old_ttl)
    return [
        (lower_by - timedelta(hours=1), f"lower TTL {old_ttl}s → {new_ttl}s (at least {old_ttl}s before the change, +1h margin)"),
        (change_at, "change the record (new IP); keep the old server running"),
        (change_at + timedelta(seconds=new_ttl), "most resolvers now see the new value (new TTL expired)"),
        (change_at + timedelta(seconds=old_ttl), "worst case: a resolver that ignored the lowered TTL — then retire the old server"),
        (change_at + timedelta(seconds=old_ttl, hours=1), f"raise TTL back (e.g. {old_ttl}s)"),
    ]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["plan"]:
        ap = argparse.ArgumentParser(prog="zone_lint.py plan")
        ap.add_argument("--old-ttl", type=int, required=True)
        ap.add_argument("--new-ttl", type=int, required=True)
        ap.add_argument("--change-at", required=True, help="UTC, e.g. 2026-11-03T02:00Z")
        a = ap.parse_args(argv[1:])
        when = datetime.fromisoformat(a.change_at.replace("Z", "+00:00")).astimezone(UTC)
        for t, what in plan(a.old_ttl, a.new_ttl, when):
            print(f"{t:%Y-%m-%d %H:%M}Z  {what}")
        return 0
    ap = argparse.ArgumentParser(description="Lint a DNS zone file.")
    ap.add_argument("zonefile", type=Path)
    ap.add_argument("--origin", default=".", help="zone name if the file has no $ORIGIN")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        text = a.zonefile.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    records, findings = parse(text, a.origin)
    zone = next((r.name for r in records if r.type == "SOA"), a.origin)
    findings += lint(records, zone)
    if a.json:
        print(json.dumps({"zone": zone, "records": len(records), "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            print(f"{f.level.upper():<7} line {f.line:<3} {f.code:<22} {f.message}")
        errors = sum(f.level == "error" for f in findings)
        print(f"{zone}: {len(records)} records, {errors} error(s), {len(findings) - errors} warning(s)")
    return 1 if any(f.level == "error" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
