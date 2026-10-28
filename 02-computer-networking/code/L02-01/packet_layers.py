#!/usr/bin/env python3
"""Encapsulation demo — একটি HTTP request-কে TCP → IPv4 → Ethernet header-এ মোড়ানো ও আবার খোলা।

বাস্তব header format (RFC 793/9293 TCP, RFC 791 IPv4, IEEE 802.3 Ethernet) অনুযায়ী byte তৈরি করে,
যাতে প্রতিটি layer কত byte যোগ করে ও কোন field কোথায় থাকে তা দেখা যায়।
এটি network-এ কিছু পাঠায় না — শুধু memory-তে byte তৈরি ও বিশ্লেষণ।

Usage:
  python3 packet_layers.py
  python3 packet_layers.py --payload "GET /health HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n" --hexdump
"""
from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass


def checksum(data: bytes) -> int:
    """Internet checksum (RFC 1071): 16-bit word-এর one's complement যোগফলের complement।"""
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def ip_bytes(ip: str) -> bytes:
    return bytes(int(x) for x in ip.split("."))


def mac_bytes(mac: str) -> bytes:
    return bytes(int(x, 16) for x in mac.split(":"))


def tcp_segment(src_port: int, dst_port: int, seq: int, payload: bytes, src_ip: str, dst_ip: str) -> bytes:
    flags = 0x18  # PSH + ACK — data পাঠানো চলমান connection-এ
    header = struct.pack("!HHIIBBHHH", src_port, dst_port, seq, 1, 5 << 4, flags, 64240, 0, 0)
    pseudo = ip_bytes(src_ip) + ip_bytes(dst_ip) + struct.pack("!BBH", 0, 6, len(header) + len(payload))
    csum = checksum(pseudo + header + payload)
    return header[:16] + struct.pack("!H", csum) + header[18:] + payload


def ipv4_packet(src_ip: str, dst_ip: str, payload: bytes, ttl: int = 64) -> bytes:
    header = struct.pack("!BBHHHBBH4s4s", (4 << 4) | 5, 0, 20 + len(payload), 0x1C46, 0x4000, ttl, 6, 0,
                         ip_bytes(src_ip), ip_bytes(dst_ip))
    csum = checksum(header)
    return header[:10] + struct.pack("!H", csum) + header[12:] + payload


def ethernet_frame(src_mac: str, dst_mac: str, payload: bytes) -> bytes:
    return mac_bytes(dst_mac) + mac_bytes(src_mac) + struct.pack("!H", 0x0800) + payload  # 0x0800 = IPv4


@dataclass
class Decoded:
    dst_mac: str
    src_mac: str
    ethertype: int
    src_ip: str
    dst_ip: str
    ttl: int
    ip_header_ok: bool
    src_port: int
    dst_port: int
    payload: bytes


def decode(frame: bytes) -> Decoded:
    dst, src, ethertype = frame[0:6], frame[6:12], struct.unpack("!H", frame[12:14])[0]
    ip = frame[14:]
    ihl = (ip[0] & 0x0F) * 4
    ttl = ip[8]
    total_len = struct.unpack("!H", ip[2:4])[0]
    tcp = ip[ihl:total_len]
    data_offset = (tcp[12] >> 4) * 4
    sport, dport = struct.unpack("!HH", tcp[0:4])
    fmt = lambda b: ":".join(f"{x:02x}" for x in b)  # noqa: E731
    return Decoded(fmt(dst), fmt(src), ethertype, ".".join(map(str, ip[12:16])), ".".join(map(str, ip[16:20])),
                   ttl, checksum(ip[:ihl]) == 0, sport, dport, tcp[data_offset:])


def build(payload: bytes) -> tuple[bytes, list[tuple[str, int]]]:
    seg = tcp_segment(51544, 80, 1000, payload, "192.168.1.10", "93.184.215.14")
    pkt = ipv4_packet("192.168.1.10", "93.184.215.14", seg)
    frame = ethernet_frame("52:54:00:12:34:56", "52:54:00:ab:cd:ef", pkt)
    sizes = [("L7 application (HTTP)", len(payload)), ("L4 TCP header", len(seg) - len(payload)),
             ("L3 IPv4 header", len(pkt) - len(seg)), ("L2 Ethernet header", len(frame) - len(pkt))]
    return frame, sizes


def hexdump(data: bytes, width: int = 16) -> str:
    return "\n".join(f"{i:04x}  {' '.join(f'{b:02x}' for b in data[i:i + width]):<{width * 3}} "
                     f"{''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i + width])}"
                     for i in range(0, len(data), width))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Show protocol encapsulation byte by byte.")
    p.add_argument("--payload", default="GET / HTTP/1.1\\r\\nHost: example.com\\r\\n\\r\\n")
    p.add_argument("--hexdump", action="store_true")
    args = p.parse_args(argv)
    payload = args.payload.encode().decode("unicode_escape").encode("latin-1")

    frame, sizes = build(payload)
    print("encapsulation (sender, top → bottom):")
    for name, n in sizes:
        print(f"  {name:24} {n:4} bytes")
    overhead = sum(n for name, n in sizes[1:])
    print(f"  {'frame total':24} {len(frame):4} bytes  (header overhead {overhead} = "
          f"{100 * overhead / len(frame):.1f}%; + 4-byte FCS ও preamble wire-এ যোগ হয়)")
    d = decode(frame)
    print("\ndecapsulation (receiver, bottom → top):")
    print(f"  L2: {d.src_mac} → {d.dst_mac}  ethertype 0x{d.ethertype:04x} (IPv4)")
    print(f"  L3: {d.src_ip} → {d.dst_ip}  TTL {d.ttl}  header checksum {'ok' if d.ip_header_ok else 'BAD'}")
    print(f"  L4: port {d.src_port} → {d.dst_port}")
    print(f"  L7: {d.payload!r}")
    if args.hexdump:
        print("\n" + hexdump(frame))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
