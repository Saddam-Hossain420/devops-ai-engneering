#!/usr/bin/env python3
"""TCP port forwarder — `ssh -L`-এর মূল ধারণা নিজের হাতে (encryption ছাড়া), শুধু standard library।

  python3 port_forward.py --listen 127.0.0.1:9000 --to 127.0.0.1:8000
  python3 port_forward.py demo        # loopback-এ echo server + forwarder, byte গণনা দেখায়

`ssh -L 9000:db.internal:5432 bastion` = একই কাজ, কিন্তু local ↔ bastion অংশটি SSH-এর encrypted
channel দিয়ে যায় এবং bastion থেকে db.internal-এ connection খোলে। এই script কোনো encryption দেয় না —
শুধু loopback বা বিশ্বস্ত network-এ শেখার জন্য।
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import time


def split_hostport(s: str) -> tuple[str, int]:
    host, sep, port = s.rpartition(":")
    if not sep or not port.isdigit():
        raise ValueError(f"expected HOST:PORT, got {s!r}")
    return host or "127.0.0.1", int(port)


class Forwarder:
    """প্রতিটি client connection-এর জন্য target-এ নতুন connection, তারপর দুই দিকে byte copy।"""

    def __init__(self, listen: tuple[str, int], target: tuple[str, int]) -> None:
        self.target = target
        self.server = socket.create_server(listen)
        self.server.settimeout(0.2)
        self.port = self.server.getsockname()[1]
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.stats = {"connections": 0, "failed": 0, "bytes_up": 0, "bytes_down": 0}
        self.threads: list[threading.Thread] = []

    def _count(self, key: str, n: int = 1) -> None:
        with self.lock:
            self.stats[key] += n

    def _pipe(self, src: socket.socket, dst: socket.socket, key: str) -> None:
        try:
            while chunk := src.recv(65536):
                dst.sendall(chunk)
                self._count(key, len(chunk))
        except OSError:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)  # অপর দিককে EOF জানানো (half-close, L02-05)
            except OSError:
                pass

    def _handle(self, client: socket.socket) -> None:
        try:
            upstream = socket.create_connection(self.target, timeout=3)
        except OSError:
            self._count("failed")
            client.close()  # target বন্ধ → client-এর connection সাথে সাথে বন্ধ
            return
        self._count("connections")
        upstream.settimeout(None)
        t = threading.Thread(target=self._pipe, args=(upstream, client, "bytes_down"), daemon=True)
        t.start()
        self._pipe(client, upstream, "bytes_up")
        t.join()
        client.close()
        upstream.close()

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                client, _ = self.server.accept()
            except (TimeoutError, OSError):
                continue
            client.settimeout(None)
            t = threading.Thread(target=self._handle, args=(client,), daemon=True)
            t.start()
            self.threads.append(t)

    def start(self) -> "Forwarder":
        threading.Thread(target=self._loop, daemon=True).start()
        return self

    def stop(self) -> None:
        self.stop_event.set()
        for t in self.threads:
            t.join(2)
        self.server.close()


def echo_server() -> tuple[socket.socket, int, threading.Event]:
    """Upper-case echo server (L02-05-এর মতো), loopback-এ।"""
    srv = socket.create_server(("127.0.0.1", 0))
    srv.settimeout(0.2)
    stop = threading.Event()

    def serve(conn: socket.socket) -> None:
        with conn:
            while data := conn.recv(65536):
                conn.sendall(data.upper())

    def loop() -> None:
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except (TimeoutError, OSError):
                continue
            conn.settimeout(None)
            threading.Thread(target=serve, args=(conn,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv, srv.getsockname()[1], stop


def roundtrip(port: int, payload: bytes) -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=3) as s:
        s.sendall(payload)
        s.shutdown(socket.SHUT_WR)
        out = b""
        while chunk := s.recv(65536):
            out += chunk
    return out


def demo() -> int:
    srv, eport, stop = echo_server()
    fw = Forwarder(("127.0.0.1", 0), ("127.0.0.1", eport)).start()
    try:
        print(f"echo server on 127.0.0.1:{eport}; forwarder 127.0.0.1:{fw.port} -> 127.0.0.1:{eport}")
        for msg in (b"hello through the tunnel", b"x" * 100_000):
            reply = roundtrip(fw.port, msg)
            print(f"sent {len(msg):>6} bytes via forwarder, got {len(reply):>6} back: {reply[:24]!r}")
        time.sleep(0.1)
        print(f"stats: {fw.stats}")
    finally:
        fw.stop()
        stop.set()
        srv.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Plain TCP port forwarder (learning tool, no encryption).")
    ap.add_argument("cmd", nargs="?", choices=["demo"])
    ap.add_argument("--listen", default="127.0.0.1:9000")
    ap.add_argument("--to")
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        return demo()
    if not args.to:
        ap.error("--to HOST:PORT is required (or use 'demo')")
    try:
        listen, target = split_hostport(args.listen), split_hostport(args.to)
        if listen[0] not in ("127.0.0.1", "::1", "localhost"):
            print("warning: listening on a non-loopback address exposes the target to the network",
                  file=sys.stderr)
        fw = Forwarder(listen, target).start()
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"forwarding {listen[0]}:{fw.port} -> {target[0]}:{target[1]}  (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(5)
            print(f"stats: {fw.stats}")
    except KeyboardInterrupt:
        fw.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
