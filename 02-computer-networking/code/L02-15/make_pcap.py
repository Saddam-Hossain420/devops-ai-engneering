#!/usr/bin/env python3
"""Synthetic pcap তৈরি — হাতে বানানো packet (সঠিক IPv4/TCP/UDP checksum সহ) দিয়ে একটি ছোট "ঘটনা":

  1. 10.0.0.5 → 10.0.0.10:80 — TCP handshake, HTTP GET, একটি retransmission, 200 OK, FIN
  2. 10.0.0.5 → 10.0.0.10:5432 — RST (port বন্ধ)
  3. 10.0.0.5 → 10.0.0.2:53 — DNS query ও উত্তর (UDP)

  python3 make_pcap.py sample.pcap

Wireshark বা `tcpdump -r sample.pcap -nn` দিয়ে খোলা যায়। কোনো আসল network traffic নয়।
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

CLIENT_MAC = bytes.fromhex("020000000005")
SERVER_MAC = bytes.fromhex("02000000000a")
BASE_TS = 1_793_000_000  # নির্দিষ্ট সময় — বারবার চালালে একই file


def checksum(data: bytes) -> int:
    """RFC 1071 internet checksum (L02-01)।"""
    if len(data) % 2:
        data += b"\x00"
    s = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def ip_bytes(ip: str) -> bytes:
    return bytes(int(x) for x in ip.split("."))


def ipv4(src: str, dst: str, proto: int, payload: bytes, ident: int) -> bytes:
    header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, 20 + len(payload), ident, 0x4000, 64, proto, 0,
                         ip_bytes(src), ip_bytes(dst))
    header = header[:10] + struct.pack("!H", checksum(header)) + header[12:]
    return header + payload


def l4_checksum(src: str, dst: str, proto: int, segment: bytes) -> int:
    pseudo = ip_bytes(src) + ip_bytes(dst) + struct.pack("!BBH", 0, proto, len(segment))
    return checksum(pseudo + segment)


def tcp(src: str, sport: int, dst: str, dport: int, seq: int, ack: int, flags: str,
        payload: bytes = b"", window: int = 64240) -> bytes:
    bits = sum({"F": 1, "S": 2, "R": 4, "P": 8, "A": 16}[f] for f in flags)
    seg = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, bits, window, 0, 0) + payload
    c = l4_checksum(src, dst, 6, seg)
    return seg[:16] + struct.pack("!H", c) + seg[18:]


def udp(src: str, sport: int, dst: str, dport: int, payload: bytes) -> bytes:
    seg = struct.pack("!HHHH", sport, dport, 8 + len(payload), 0) + payload
    c = l4_checksum(src, dst, 17, seg) or 0xFFFF
    return seg[:6] + struct.pack("!H", c) + seg[8:]


def frame(src_mac: bytes, dst_mac: bytes, ip_packet: bytes) -> bytes:
    return dst_mac + src_mac + b"\x08\x00" + ip_packet


def scenario() -> list[tuple[float, bytes]]:
    c, s, dns = "10.0.0.5", "10.0.0.10", "10.0.0.2"
    out: list[tuple[float, bytes]] = []
    ident = [100]

    def add(t: float, src: str, dst: str, proto: int, seg: bytes, to_server: bool) -> None:
        ident[0] += 1
        macs = (CLIENT_MAC, SERVER_MAC) if to_server else (SERVER_MAC, CLIENT_MAC)
        out.append((t, frame(*macs, ipv4(src, dst, proto, seg, ident[0]))))

    req = b"GET /health HTTP/1.1\r\nHost: 10.0.0.10\r\n\r\n"
    resp = b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nok\n"
    q = bytes.fromhex("abcd01000001000000000000") + b"\x03api\x07example\x03com\x00\x00\x01\x00\x01"
    a = (bytes.fromhex("abcd81800001000100000000") + b"\x03api\x07example\x03com\x00\x00\x01\x00\x01"
         + b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x01\x2c\x00\x04" + ip_bytes("10.0.0.10"))
    add(0.000000, c, dns, 17, udp(c, 40000, dns, 53, q), True)
    add(0.000800, dns, c, 17, udp(dns, 53, c, 40000, a), False)
    add(0.010000, c, s, 6, tcp(c, 51514, s, 80, 1000, 0, "S"), True)
    add(0.010450, s, c, 6, tcp(s, 80, c, 51514, 5000, 1001, "SA", window=65160), False)  # RTT 0.45 ms
    add(0.010500, c, s, 6, tcp(c, 51514, s, 80, 1001, 5001, "A"), True)
    add(0.010600, c, s, 6, tcp(c, 51514, s, 80, 1001, 5001, "PA", req), True)
    add(0.215000, c, s, 6, tcp(c, 51514, s, 80, 1001, 5001, "PA", req), True)  # ACK আসেনি → retransmit (~200 ms RTO)
    add(0.215400, s, c, 6, tcp(s, 80, c, 51514, 5001, 1001 + len(req), "A"), False)
    add(0.216000, s, c, 6, tcp(s, 80, c, 51514, 5001, 1001 + len(req), "PA", resp), False)
    add(0.216100, c, s, 6, tcp(c, 51514, s, 80, 1001 + len(req), 5001 + len(resp), "A"), True)
    add(0.216200, c, s, 6, tcp(c, 51514, s, 80, 1001 + len(req), 5001 + len(resp), "FA"), True)
    add(0.216500, s, c, 6, tcp(s, 80, c, 51514, 5001 + len(resp), 1002 + len(req), "FA"), False)
    add(0.216600, c, s, 6, tcp(c, 51514, s, 80, 1002 + len(req), 5002 + len(resp), "A"), True)
    add(0.300000, c, s, 6, tcp(c, 51600, s, 5432, 9000, 0, "S"), True)
    add(0.300300, s, c, 6, tcp(s, 5432, c, 51600, 0, 9001, "RA", window=0), False)  # port বন্ধ
    return out


def write_pcap(path: Path, packets: list[tuple[float, bytes]], big_endian: bool = False) -> None:
    e = ">" if big_endian else "<"
    data = struct.pack(e + "IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)  # linktype 1 = Ethernet
    for t, pkt in packets:
        sec, usec = BASE_TS + int(t), round((t % 1) * 1_000_000)
        data += struct.pack(e + "IIII", sec, usec, len(pkt), len(pkt)) + pkt
    path.write_bytes(data)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a small synthetic pcap file.")
    ap.add_argument("out", type=Path)
    args = ap.parse_args(argv)
    pkts = scenario()
    write_pcap(args.out, pkts)
    print(f"wrote {len(pkts)} packets to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
