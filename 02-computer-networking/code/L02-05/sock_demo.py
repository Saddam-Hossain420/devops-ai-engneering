#!/usr/bin/env python3
"""TCP ও UDP socket demo — শুধু 127.0.0.1 (loopback)-এ; বাইরে কিছু পাঠায় না।

Commands:
  python3 sock_demo.py tcp          # TCP echo: listen → accept → recv/send → close, handshake সময় সহ
  python3 sock_demo.py udp          # UDP echo: connection ছাড়া datagram
  python3 sock_demo.py refused      # বন্ধ port-এ connect → RST → ConnectionRefusedError
  python3 sock_demo.py latency --n 200   # loopback-এ connect (3-way handshake) সময়ের বণ্টন
"""
from __future__ import annotations

import argparse
import socket
import statistics
import sys
import threading
import time


def tcp_echo_server() -> tuple[socket.socket, int, threading.Thread]:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))           # port 0: OS খালি port দেয়
    srv.listen(16)                       # backlog: accept-এর অপেক্ষায় থাকা connection-এর সারি

    def serve() -> None:
        while True:
            try:
                conn, _ = srv.accept()   # 3-way handshake শেষ হলে নতুন socket
            except OSError:
                return                    # server বন্ধ
            with conn:
                while data := conn.recv(4096):
                    conn.sendall(data.upper())

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return srv, srv.getsockname()[1], t


def tcp_roundtrip(port: int, message: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as c:
        c.sendall(message)
        c.shutdown(socket.SHUT_WR)       # "আর পাঠাবো না" — FIN পাঠায়, server-এর recv() b"" পায়
        chunks = []
        while data := c.recv(4096):
            chunks.append(data)
    return b"".join(chunks)


def udp_roundtrip(message: bytes) -> bytes:
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]

    def serve_once() -> None:
        data, addr = srv.recvfrom(65535)  # একটি datagram, কে পাঠালো সহ
        srv.sendto(data.upper(), addr)

    t = threading.Thread(target=serve_once, daemon=True)
    t.start()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as c:
        c.settimeout(3)                   # UDP-তে উত্তরের নিশ্চয়তা নেই — timeout অপরিহার্য
        c.sendto(message, ("127.0.0.1", port))
        reply, _ = c.recvfrom(65535)
    t.join(1)
    srv.close()
    return reply


def closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()                             # এখন কেউ শুনছে না
    return port


def connect_refused(port: int) -> str:
    try:
        socket.create_connection(("127.0.0.1", port), timeout=3).close()
        return "connected (unexpected)"
    except ConnectionRefusedError as exc:
        return f"ConnectionRefusedError errno={exc.errno} — port বন্ধ, kernel RST পাঠিয়েছে"


def connect_latency(port: int, n: int) -> list[float]:
    times = []
    for _ in range(n):
        start = time.perf_counter()
        socket.create_connection(("127.0.0.1", port), timeout=3).close()
        times.append((time.perf_counter() - start) * 1_000_000)  # microseconds
    return times


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="TCP/UDP socket demonstrations on loopback.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("tcp")
    sub.add_parser("udp")
    sub.add_parser("refused")
    lp = sub.add_parser("latency")
    lp.add_argument("--n", type=int, default=200)
    args = p.parse_args(argv)

    if args.cmd == "tcp":
        srv, port, _ = tcp_echo_server()
        print(f"TCP server listening on 127.0.0.1:{port}")
        print(f"reply: {tcp_roundtrip(port, b'hello over tcp')!r}")
        srv.close()
    elif args.cmd == "udp":
        print(f"reply: {udp_roundtrip(b'hello over udp')!r}")
    elif args.cmd == "refused":
        print(connect_refused(closed_port()))
    else:
        srv, port, _ = tcp_echo_server()
        times = sorted(connect_latency(port, args.n))
        p50 = times[len(times) // 2]
        p99 = times[min(len(times) - 1, int(len(times) * 0.99))]
        print(f"{args.n} connects on loopback: min {times[0]:.0f}µs  p50 {p50:.0f}µs  "
              f"p99 {p99:.0f}µs  mean {statistics.mean(times):.0f}µs")
        srv.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
