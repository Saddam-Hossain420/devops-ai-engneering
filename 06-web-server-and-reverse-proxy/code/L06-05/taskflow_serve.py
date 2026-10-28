#!/usr/bin/env python3
"""taskflow_serve.py — TaskFlow API (L05-13)-কে তিনভাবে চালানো: TCP port, unix socket, বা systemd socket activation।

  python3 taskflow_serve.py --tcp 127.0.0.1:8000
  python3 taskflow_serve.py --unix /run/taskflow/taskflow.sock --mode 660        # Linux
  (systemd taskflow.socket থেকে চালু হলে কোনো option লাগে না — LISTEN_FDS দেখে fd 3 ব্যবহার করে)

Socket activation-এর চুক্তি (sd_listen_fds): env LISTEN_PID = এই process-এর PID, LISTEN_FDS = সংখ্যা, fd ৩ থেকে শুরু।
systemd আগে থেকেই socket ধরে রাখে, তাই app restart-এর সময়ও nginx-এর connection queue-তে অপেক্ষা করে — refused নয়।
"""
from __future__ import annotations

import argparse
import os
import signal
import socket
import socketserver
import sys
import threading
from collections.abc import Mapping
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "05-python-for-infrastructure" / "code" / "L05-13"))
import taskflow_api as tf  # noqa: E402

SD_LISTEN_FDS_START = 3


def listen_fds(environ: Mapping[str, str], pid: int) -> int:
    """systemd-এর দেওয়া listening socket-এর সংখ্যা; এই process-এর জন্য না হলে ০ (child-এ ভুল করে না নেওয়া)।"""
    if environ.get("LISTEN_PID") != str(pid):
        return 0
    try:
        return max(0, int(environ.get("LISTEN_FDS", "0")))
    except ValueError:
        return 0


class _Threading(socketserver.ThreadingMixIn):
    daemon_threads = False
    block_on_close = True


def server_from_socket(sock: socket.socket, store: tf.Store) -> socketserver.BaseServer:
    handler = type("BoundHandler", (tf.Handler,), {"store": store})
    if sock.family == getattr(socket, "AF_UNIX", None):
        base: type = socketserver.UnixStreamServer
    else:
        base = socketserver.TCPServer
    cls = type("ActivatedServer", (_Threading, base), {})
    srv = cls(sock.getsockname(), handler, bind_and_activate=False)
    srv.socket.close()                                   # নিজের বানানো socket বাদ, দেওয়াটা ব্যবহার
    srv.socket = sock
    return srv


def make_unix_server(path: str, mode: int, store: tf.Store) -> socketserver.BaseServer:
    if not hasattr(socket, "AF_UNIX") or not hasattr(socketserver, "UnixStreamServer"):
        raise SystemExit("error: unix sockets are not available on this platform (use --tcp)")
    p = Path(path)
    if p.exists() and p.is_socket():                     # আগের run-এর পুরোনো socket file
        p.unlink()
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    old = os.umask(0o777 & ~mode)                        # bind-এর মুহূর্তেই সঠিক permission — পরে chmod-এর race নয়
    try:
        sock.bind(path)
    finally:
        os.umask(old)
    sock.listen(128)
    return server_from_socket(sock, store)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Serve TaskFlow over TCP, a unix socket, or systemd socket activation.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--tcp", help="HOST:PORT")
    g.add_argument("--unix", help="socket path")
    ap.add_argument("--mode", default="660", help="unix socket permission (octal, default 660)")
    a = ap.parse_args(argv)
    cfg = tf.Config.from_env()
    tf.setup_logging(cfg.log_level)
    store = tf.Store(cfg.db_path)
    store.migrate()

    n = listen_fds(os.environ, os.getpid())
    if n:
        sock = socket.socket(fileno=SD_LISTEN_FDS_START)
        srv, where = server_from_socket(sock, store), f"systemd socket fd {SD_LISTEN_FDS_START}"
        for k in ("LISTEN_PID", "LISTEN_FDS", "LISTEN_FDNAMES"):
            os.environ.pop(k, None)                       # child process-এ যেন না যায়
    elif a.unix:
        srv, where = make_unix_server(a.unix, int(a.mode, 8), store), f"unix:{a.unix}"
    else:
        host, _, port = (a.tcp or f"{cfg.host}:{cfg.port}").rpartition(":")
        srv = tf.make_server(tf.Config(host, int(port), cfg.db_path, cfg.log_level))
        where = f"http://{host}:{srv.server_address[1]}"
    tf.log.info("listening", extra={"on": where, "version": tf.__version__})

    def stop(signum: int, _frame: object) -> None:
        tf.log.info("shutdown requested", extra={"signal": signal.Signals(signum).name})
        threading.Thread(target=srv.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)
    try:
        srv.serve_forever(poll_interval=0.2)
    finally:
        srv.server_close()
        if a.unix and not n:
            Path(a.unix).unlink(missing_ok=True)
        tf.log.info("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
