#!/usr/bin/env python3
"""pcap file পড়ে tcpdump-এর মতো এক-লাইনের সারাংশ ও TCP বিশ্লেষণ (handshake RTT, retransmission, RST,
zero window), শুধু standard library। Ethernet (802.1Q tag সহ), IPv4, TCP, UDP।

  sudo tcpdump -ni any -w /tmp/cap.pcap ...   # Ubuntu-তে আসল capture (Linux "any" = linktype 113, সমর্থিত)
  python3 pcap_summary.py sample.pcap
  python3 pcap_summary.py sample.pcap --analyze-only

Exit: 0 সমস্যা নেই, 1 retransmission/RST পাওয়া গেছে, 2 file পড়া/format error।
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

FLAG_NAMES = [(0x02, "S"), (0x01, "F"), (0x04, "R"), (0x08, "P"), (0x10, ".")]  # tcpdump-এর অক্ষর ও ক্রম


@dataclass
class Pkt:
    ts: float
    src: str
    dst: str
    proto: str          # TCP | UDP | ICMP | other
    sport: int = 0
    dport: int = 0
    flags: int = 0
    seq: int = 0
    ack: int = 0
    window: int = 0
    length: int = 0     # L4 payload

    def flag_str(self) -> str:
        return "".join(ch for bit, ch in FLAG_NAMES if self.flags & bit) or "none"


def read_pcap(data: bytes) -> tuple[int, list[tuple[float, bytes]]]:
    """(linktype, [(timestamp, frame)])। Little/big-endian ও nanosecond variant।"""
    if len(data) < 24:
        raise ValueError("file too short for a pcap header")
    magic = data[:4]
    formats = {b"\xd4\xc3\xb2\xa1": ("<", 1e6), b"\xa1\xb2\xc3\xd4": (">", 1e6),
               b"\x4d\x3c\xb2\xa1": ("<", 1e9), b"\xa1\xb2\x3c\x4d": (">", 1e9)}
    if magic not in formats:
        raise ValueError("not a classic pcap file (pcapng? convert: editcap -F pcap in.pcapng out.pcap)")
    e, div = formats[magic]
    linktype = struct.unpack(e + "I", data[20:24])[0]
    out, off = [], 24
    while off < len(data):
        if off + 16 > len(data):
            raise ValueError(f"truncated record header at byte {off}")
        sec, frac, incl, _orig = struct.unpack(e + "IIII", data[off:off + 16])
        off += 16
        if off + incl > len(data):
            raise ValueError(f"truncated packet at byte {off}")
        out.append((sec + frac / div, data[off:off + incl]))
        off += incl
    return linktype, out


def decode(ts: float, frame: bytes, linktype: int) -> Pkt | None:
    if linktype == 1:                    # Ethernet
        etype, off = struct.unpack("!H", frame[12:14])[0], 14
        if etype == 0x8100:              # 802.1Q VLAN tag (L02-02)
            etype, off = struct.unpack("!H", frame[16:18])[0], 18
    elif linktype == 113:                # Linux cooked capture (tcpdump -i any)
        etype, off = struct.unpack("!H", frame[14:16])[0], 16
    else:
        return None
    if etype != 0x0800 or len(frame) < off + 20:
        return None
    ip = frame[off:]
    ihl = (ip[0] & 0x0F) * 4
    total, proto = struct.unpack("!H", ip[2:4])[0], ip[9]
    src, dst = ".".join(map(str, ip[12:16])), ".".join(map(str, ip[16:20]))
    l4 = ip[ihl:total]
    if proto == 6 and len(l4) >= 20:
        sport, dport, seq, ack, off_byte, flags, window = struct.unpack("!HHIIBBH", l4[:16])
        return Pkt(ts, src, dst, "TCP", sport, dport, flags, seq, ack, window, len(l4) - (off_byte >> 4) * 4)
    if proto == 17 and len(l4) >= 8:
        sport, dport = struct.unpack("!HH", l4[:4])
        return Pkt(ts, src, dst, "UDP", sport, dport, length=len(l4) - 8)
    return Pkt(ts, src, dst, "ICMP" if proto == 1 else f"proto-{proto}", length=len(l4))


def line(p: Pkt) -> str:
    t = datetime.fromtimestamp(p.ts, tz=timezone.utc).strftime("%H:%M:%S.%f")
    if p.proto == "TCP":
        ack = f", ack {p.ack}" if p.flags & 0x10 else ""
        return (f"{t} IP {p.src}.{p.sport} > {p.dst}.{p.dport}: Flags [{p.flag_str()}], seq {p.seq}{ack}, "
                f"win {p.window}, length {p.length}")
    if p.proto == "UDP":
        return f"{t} IP {p.src}.{p.sport} > {p.dst}.{p.dport}: UDP, length {p.length}"
    return f"{t} IP {p.src} > {p.dst}: {p.proto}, length {p.length}"


def analyze(pkts: list[Pkt]) -> list[str]:
    findings, syn_time, seen = [], {}, set()
    for p in pkts:
        if p.proto != "TCP":
            continue
        fwd = (p.src, p.sport, p.dst, p.dport)
        if p.flags & 0x02 and not p.flags & 0x10:
            syn_time[fwd] = p.ts
        elif p.flags & 0x12 == 0x12:
            rev = (p.dst, p.dport, p.src, p.sport)
            if rev in syn_time:
                findings.append(f"handshake {rev[0]}:{rev[1]} → {rev[2]}:{rev[3]}  RTT "
                                f"{(p.ts - syn_time.pop(rev)) * 1000:.2f} ms")
        if p.length > 0:
            key = fwd + (p.seq, p.length)
            if key in seen:
                findings.append(f"RETRANSMISSION {p.src}:{p.sport} → {p.dst}:{p.dport} seq {p.seq} "
                                f"length {p.length} — packet or its ACK was lost")
            seen.add(key)
        if p.flags & 0x04:
            findings.append(f"RST {p.src}:{p.sport} → {p.dst}:{p.dport} — connection refused/aborted "
                            "(closed port, firewall reject, or app crash)")
        elif p.window == 0 and not p.flags & 0x02:
            findings.append(f"ZERO WINDOW from {p.src}:{p.sport} — receiver not reading fast enough")
    return findings


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Summarize and analyze a pcap file.")
    ap.add_argument("pcap", type=Path)
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args(argv)
    try:
        linktype, records = read_pcap(args.pcap.read_bytes())
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    pkts = [p for p in (decode(ts, f, linktype) for ts, f in records) if p]
    if not args.analyze_only:
        for p in pkts:
            print(line(p))
        print()
    talkers = Counter(f"{p.src} → {p.dst}" for p in pkts)
    print(f"{len(records)} packets ({len(pkts)} IPv4), protocols {dict(Counter(p.proto for p in pkts))}")
    print("top talkers: " + ", ".join(f"{k} ({v})" for k, v in talkers.most_common(3)))
    findings = analyze(pkts)
    for f in findings:
        print(f"- {f}")
    bad = [f for f in findings if not f.startswith("handshake")]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
