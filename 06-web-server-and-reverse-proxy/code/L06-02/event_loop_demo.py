#!/usr/bin/env python3
"""event_loop_demo.py — nginx কেন event loop: ধীর client (slowloris-ধাঁচ) thread-pool server-কে আটকায়, event loop-কে নয়।

  python3 event_loop_demo.py                    # দুই server, ২০টি ধীর client, তারপর একটি সাধারণ request-এর সময়
  python3 event_loop_demo.py --slow 200 --workers 20

দুটি ছোট HTTP server (127.0.0.1, OS-নির্বাচিত port), দুটোই একই কাজ করে: request header শেষ হলে "ok"।
  threaded : প্রতিটি connection একটি worker thread নেয় (pool-এ --workers টি) — Apache prefork/worker-এর মতো
  event    : একটি thread, selectors দিয়ে সব connection — nginx worker-এর মতো
ধীর client header-এর অর্ধেক পাঠিয়ে চুপ করে থাকে। প্রতিটি server-এ header timeout --header-timeout s।
"""
from __future__ import annotations

import argparse
import selectors
import socket
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

RESPONSE = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"


def threaded_server(workers: int, header_timeout: float) -> tuple[socket.socket, threading.Event]:
    srv = socket.create_server(("127.0.0.1", 0), backlog=1024)
    stop = threading.Event()
    pool = ThreadPoolExecutor(max_workers=workers)
    queued: list[tuple[Future[None], socket.socket]] = []

    def handle(conn: socket.socket) -> None:
        with conn:
            conn.settimeout(header_timeout)
            buf = b""
            try:
                while b"\r\n\r\n" not in buf:
                    chunk = conn.recv(4096)
                    if not chunk:
                        return
                    buf += chunk
                conn.sendall(RESPONSE)
            except OSError:                        # timeout বা reset — worker মুক্ত হয়
                return

    def accept_loop() -> None:
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            queued.append((pool.submit(handle, conn), conn))     # সব worker ব্যস্ত হলে queue-তে অপেক্ষা
        pool.shutdown(wait=False, cancel_futures=True)
        for fut, conn in queued:                   # কখনো শুরু না হওয়া কাজের socket নিজে বন্ধ করা
            if fut.cancelled():
                conn.close()

    threading.Thread(target=accept_loop, daemon=True).start()
    return srv, stop


def event_server(header_timeout: float) -> tuple[socket.socket, threading.Event]:
    srv = socket.create_server(("127.0.0.1", 0), backlog=1024)
    srv.setblocking(False)
    stop = threading.Event()
    sel = selectors.DefaultSelector()
    sel.register(srv, selectors.EVENT_READ, None)

    def loop() -> None:
        state: dict[socket.socket, tuple[bytes, float]] = {}
        while not stop.is_set():
            for key, _ in sel.select(timeout=0.2):
                if key.data is None:                                   # নতুন connection
                    try:
                        conn, _ = srv.accept()
                    except BlockingIOError:
                        continue
                    conn.setblocking(False)
                    sel.register(conn, selectors.EVENT_READ, "client")
                    state[conn] = (b"", time.monotonic())
                    continue
                conn = key.fileobj
                assert isinstance(conn, socket.socket)
                try:
                    chunk = conn.recv(4096)
                except (BlockingIOError, InterruptedError):
                    continue
                except OSError:
                    chunk = b""
                buf = state[conn][0] + chunk
                if not chunk or b"\r\n\r\n" in buf:
                    if chunk:
                        try:
                            conn.sendall(RESPONSE)                    # ছোট response — buffer-এ ঢুকে যায়
                        except OSError:
                            pass
                    sel.unregister(conn)
                    conn.close()
                    state.pop(conn, None)
                else:
                    state[conn] = (buf, state[conn][1])
            now = time.monotonic()                                     # header timeout (nginx: client_header_timeout)
            for conn, (_, started) in list(state.items()):
                if now - started > header_timeout:
                    sel.unregister(conn)
                    conn.close()
                    del state[conn]
        for conn in state:                                             # বন্ধের সময় বাকি connection
            conn.close()
        sel.close()

    threading.Thread(target=loop, daemon=True).start()
    return srv, stop


def timed_request(port: int, timeout: float = 30.0) -> float:
    start = time.monotonic()
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
        s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    if not data.endswith(b"ok"):
        raise RuntimeError(f"unexpected response {data[:60]!r}")
    return time.monotonic() - start


def run(kind: str, slow: int, workers: int, header_timeout: float) -> tuple[float, int]:
    srv, stop = threaded_server(workers, header_timeout) if kind == "threaded" else event_server(header_timeout)
    port = srv.getsockname()[1]
    slow_clients = []
    for _ in range(slow):
        s = socket.create_connection(("127.0.0.1", port))
        s.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n")                # অর্ধেক header, তারপর চুপ
        slow_clients.append(s)
    time.sleep(0.3)                                                    # server সবগুলো accept করুক
    threads_before = threading.active_count()
    try:
        took = timed_request(port)
    except TimeoutError:                                               # নিজেই একটি ফল: server সাড়া দেয়নি
        took = float("inf")
    for s in slow_clients:
        s.close()
    stop.set()
    srv.close()
    return took, threads_before


def main() -> None:
    ap = argparse.ArgumentParser(description="Slow clients vs thread pool and event loop.")
    ap.add_argument("--slow", type=int, default=20)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--header-timeout", type=float, default=3.0)
    a = ap.parse_args()
    print(f"{a.slow} slow clients, {a.workers} worker threads (threaded), header timeout {a.header_timeout}s")
    for kind in ("event", "threaded"):
        took, threads = run(kind, a.slow, a.workers, a.header_timeout)
        result = "NO ANSWER within 30 s" if took == float("inf") else f"answered in {took * 1000:8.1f} ms"
        print(f"{kind:<9} normal request {result}   (python threads alive: {threads})")


if __name__ == "__main__":
    main()
