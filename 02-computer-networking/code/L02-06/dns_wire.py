#!/usr/bin/env python3
"""DNS wire format — নিজের হাতে DNS query তৈরি ও response parse (RFC 1035), শুধু standard library।

Commands:
  python3 dns_wire.py query example.com A                 # system resolver (/etc/resolv.conf-এর প্রথম nameserver)
  python3 dns_wire.py query example.com MX --server 1.1.1.1
  python3 dns_wire.py build example.com A                 # query-র byte (hex) — network ছাড়া

শেখার tool; production-এ dig/resolvectl বা dnspython ব্যবহার করুন।
"""
from __future__ import annotations

import argparse
import random
import socket
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

TYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16, "AAAA": 28}
TYPE_NAMES = {v: k for k, v in TYPES.items()}
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}


def encode_name(name: str) -> bytes:
    """'www.example.com' → \\x03www\\x07example\\x03com\\x00 (প্রতিটি label-এর আগে দৈর্ঘ্য)."""
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode("idna")
        if not 0 < len(raw) <= 63:
            raise ValueError(f"invalid label {label!r} (1-63 bytes)")
        out += bytes([len(raw)]) + raw
    return out + b"\x00"


def build_query(name: str, qtype: str, qid: int | None = None, recursion: bool = True) -> bytes:
    qid = random.randint(0, 0xFFFF) if qid is None else qid
    flags = 0x0100 if recursion else 0  # RD bit: "resolver, পুরো কাজটা করে দাও"
    header = struct.pack("!HHHHHH", qid, flags, 1, 0, 0, 0)
    return header + encode_name(name) + struct.pack("!HH", TYPES[qtype], 1)  # class IN


def read_name(msg: bytes, offset: int, depth: int = 0) -> tuple[str, int]:
    """Name পড়া, compression pointer (0b11xxxxxx) অনুসরণ করে। (name, পরের offset)."""
    if depth > 10:
        raise ValueError("compression pointer loop")
    labels = []
    while True:
        length = msg[offset]
        if length & 0xC0 == 0xC0:  # pointer: বাকি নাম message-এর অন্য জায়গায়
            pointer = struct.unpack("!H", msg[offset:offset + 2])[0] & 0x3FFF
            rest, _ = read_name(msg, pointer, depth + 1)
            labels.append(rest)
            return ".".join(x for x in labels if x), offset + 2
        if length == 0:
            return ".".join(labels), offset + 1
        labels.append(msg[offset + 1:offset + 1 + length].decode("ascii", errors="replace"))
        offset += 1 + length


@dataclass
class Record:
    name: str
    rtype: str
    ttl: int
    value: str


@dataclass
class Response:
    qid: int
    authoritative: bool
    recursion_available: bool
    truncated: bool
    rcode: str
    question: str
    answers: list[Record]


def parse_rdata(msg: bytes, rtype: int, start: int, length: int) -> str:
    data = msg[start:start + length]
    if rtype == 1:
        return socket.inet_ntop(socket.AF_INET, data)
    if rtype == 28:
        return socket.inet_ntop(socket.AF_INET6, data)
    if rtype in (2, 5):
        return read_name(msg, start)[0]
    if rtype == 15:
        pref = struct.unpack("!H", data[:2])[0]
        return f"{pref} {read_name(msg, start + 2)[0]}"
    if rtype == 16:
        parts, i = [], 0
        while i < len(data):
            n = data[i]
            parts.append(data[i + 1:i + 1 + n].decode("utf-8", errors="replace"))
            i += 1 + n
        return " ".join(f'"{p}"' for p in parts)
    return data.hex()


def parse_response(msg: bytes) -> Response:
    if len(msg) < 12:
        raise ValueError("message shorter than DNS header")
    qid, flags, qd, an, _ns, _ar = struct.unpack("!HHHHHH", msg[:12])
    offset, question = 12, ""
    for _ in range(qd):
        question, offset = read_name(msg, offset)
        offset += 4  # qtype + qclass
    answers = []
    for _ in range(an):
        name, offset = read_name(msg, offset)
        rtype, _rclass, ttl, rdlen = struct.unpack("!HHIH", msg[offset:offset + 10])
        offset += 10
        answers.append(Record(name, TYPE_NAMES.get(rtype, str(rtype)), ttl, parse_rdata(msg, rtype, offset, rdlen)))
        offset += rdlen
    return Response(qid, bool(flags & 0x0400), bool(flags & 0x0080), bool(flags & 0x0200),
                    RCODES.get(flags & 0x000F, str(flags & 0x000F)), question, answers)


def system_nameserver(resolv: Path = Path("/etc/resolv.conf")) -> str:
    try:
        for line in resolv.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                return parts[1]
    except OSError:
        pass
    raise ValueError("no nameserver found — use --server")


def query(name: str, qtype: str, server: str, port: int = 53, timeout: float = 3.0) -> Response:
    q = build_query(name, qtype)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.sendto(q, (server, port))
        data, _ = s.recvfrom(4096)
    resp = parse_response(data)
    if resp.qid != struct.unpack("!H", q[:2])[0]:
        raise ValueError("response ID mismatch — spoofed or stale reply?")
    return resp


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Build and parse DNS messages by hand.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("name")
    b.add_argument("type", choices=TYPES)
    q = sub.add_parser("query")
    q.add_argument("name")
    q.add_argument("type", choices=TYPES)
    q.add_argument("--server")
    q.add_argument("--port", type=int, default=53)
    args = p.parse_args(argv)
    try:
        if args.cmd == "build":
            print(build_query(args.name, args.type, qid=0x1234).hex())
            return 0
        server = args.server or system_nameserver()
        r = query(args.name, args.type, server, args.port)
    except (ValueError, OSError) as exc:  # socket.timeout OSError-এর subclass
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"server {server}  status {r.rcode}  authoritative {r.authoritative}  "
          f"recursion-available {r.recursion_available}  truncated {r.truncated}")
    for rec in r.answers:
        print(f"  {rec.name:30} {rec.ttl:>7}  {rec.rtype:5} {rec.value}")
    return 0 if r.rcode == "NOERROR" else 1


if __name__ == "__main__":
    raise SystemExit(main())
