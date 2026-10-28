"""Tests for taskflow_serve.py, socket_check.py ও unit file — চালানো: python3 -m unittest -v

Unix socket ও আসল socket activation-এর test শুধু POSIX-এ চলে (Windows Python-এ AF_UNIX নেই)।
"""
from __future__ import annotations

import configparser
import http.client
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import socket_check as sc  # noqa: E402
import taskflow_serve as ts  # noqa: E402

ts.tf.log.disabled = True
POSIX_UNIX = os.name == "posix" and hasattr(socket, "AF_UNIX")


class ListenFdsTest(unittest.TestCase):
    def test_only_for_this_pid(self) -> None:
        self.assertEqual(ts.listen_fds({"LISTEN_PID": "42", "LISTEN_FDS": "1"}, 42), 1)
        self.assertEqual(ts.listen_fds({"LISTEN_PID": "41", "LISTEN_FDS": "1"}, 42), 0)   # parent-এর জন্য, আমাদের নয়
        self.assertEqual(ts.listen_fds({"LISTEN_PID": "42", "LISTEN_FDS": "x"}, 42), 0)
        self.assertEqual(ts.listen_fds({}, 42), 0)


class ProvidedSocketTest(unittest.TestCase):
    def test_serves_on_a_socket_it_did_not_create(self) -> None:
        sock = socket.create_server(("127.0.0.1", 0))                   # "systemd" আগে থেকে বানিয়েছে
        port = sock.getsockname()[1]
        with tempfile.TemporaryDirectory() as d:
            store = ts.tf.Store(str(Path(d, "t.db")))
            store.migrate()
            srv = ts.server_from_socket(sock, store)
            threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/ready")
            self.assertEqual(conn.getresponse().status, 200)
            conn.close()
            srv.shutdown()
            srv.server_close()

    @unittest.skipUnless(POSIX_UNIX, "unix sockets need POSIX")
    def test_unix_socket_mode_and_request(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d, "t.sock"))
            store = ts.tf.Store(str(Path(d, "t.db")))
            store.migrate()
            srv = ts.make_unix_server(path, 0o660, store)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o660)          # umask দিয়ে bind-এর মুহূর্তেই
            threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
            c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            c.connect(path)
            c.sendall(b"GET /health HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
            self.assertTrue(c.recv(100).startswith(b"HTTP/1.1 200"))
            c.close()
            srv.shutdown()
            srv.server_close()

    @unittest.skipUnless(POSIX_UNIX, "socket activation needs POSIX fd passing")
    def test_real_socket_activation(self) -> None:
        listener = socket.create_server(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        launcher = textwrap.dedent(f"""
            import os, sys
            os.dup2({listener.fileno()}, 3)
            os.environ.update(LISTEN_PID=str(os.getpid()), LISTEN_FDS="1")
            os.execv(sys.executable, [sys.executable, {str(HERE / 'taskflow_serve.py')!r}])
        """)
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, "TASKFLOW_DB": str(Path(d, "a.db"))}
            proc = subprocess.Popen([sys.executable, "-c", launcher], env=env, pass_fds=(listener.fileno(),),
                                    stderr=subprocess.PIPE, text=True)
            listener.close()                                               # শুধু child ধরে রাখে, systemd-এর মতো
            try:
                assert proc.stderr is not None
                self.assertIn("systemd socket fd 3", proc.stderr.readline())
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", "/health")
                self.assertEqual(conn.getresponse().status, 200)
                conn.close()
            finally:
                proc.terminate()
                proc.wait(timeout=10)
                if proc.stderr:
                    proc.stderr.close()


class SocketCheckTest(unittest.TestCase):
    def run_fake(self, layout: str, path: str, user: str = "www-data") -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            code = sc.main([path, "--user", user, "--fake-fs", str(HERE / layout)])
        return code, out.getvalue()

    def test_home_directory_blocks_even_a_0777_socket(self) -> None:
        code, out = self.run_fake("layout-home.json", "/home/ana/taskflow/taskflow.sock")
        self.assertEqual(code, 1)
        self.assertIn("blocked at /home/ana", out)

    def test_socket_unit_layout(self) -> None:
        self.assertEqual(self.run_fake("layout-run.json", "/run/taskflow/taskflow.sock")[0], 0)
        self.assertIn("blocked at /run/taskflow/taskflow.sock",
                      self.run_fake("layout-run.json", "/run/taskflow/taskflow.sock", "nobody")[1])
        self.assertIn("does not exist", self.run_fake("layout-run.json", "/run/taskflow/x.sock")[1])

    def test_permission_bits(self) -> None:
        who = sc.Identity("w", 33, frozenset({33}))
        sock = sc.Node("/s", 998, 33, 0o660, "socket")
        self.assertEqual(sc.allowed(sock, who, "w"), (True, "group"))
        self.assertEqual(sc.allowed(sc.Node("/s", 33, 0, 0o060, "socket"), who, "w"), (False, "owner"))  # owner আগে
        self.assertEqual(sc.allowed(sock, sc.Identity("root", 0, frozenset()), "w"), (True, "root"))

    def test_space_in_path(self) -> None:
        spec = {"users": {"www-data": {"uid": 33, "groups": [33]}},
                "paths": {"/": {"uid": 0, "gid": 0, "mode": "0755", "type": "dir"},
                          "/srv my": {"uid": 0, "gid": 0, "mode": "0700", "type": "dir"},
                          "/srv my/a.sock": {"uid": 0, "gid": 33, "mode": "0660", "type": "socket"}}}
        with tempfile.TemporaryDirectory() as d:
            f = Path(d, "l.json")
            f.write_text(json.dumps(spec), encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                sc.main(["/srv my/a.sock", "--fake-fs", str(f)])
        self.assertIn("blocked at /srv my —", out.getvalue())


class UnitFileTest(unittest.TestCase):
    def test_socket_unit(self) -> None:
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        cp.optionxform = str                                               # systemd key case-sensitive
        cp.read(HERE / "taskflow.socket", encoding="utf-8")
        s = cp["Socket"]
        self.assertEqual((s["ListenStream"], s["SocketGroup"], s["SocketMode"]),
                         ("/run/taskflow/taskflow.sock", "www-data", "0660"))

    def test_service_requires_socket_and_lints_clean(self) -> None:
        text = (HERE / "taskflow.service").read_text(encoding="utf-8")
        self.assertIn("Requires=taskflow.socket", text)
        lint = HERE.parents[2] / "01-linux-systems" / "code" / "L01-10" / "unit_lint.py"
        if not lint.is_file():
            self.skipTest("L01-10 unit_lint.py not found")
        r = subprocess.run([sys.executable, str(lint), str(HERE / "taskflow.service")],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
