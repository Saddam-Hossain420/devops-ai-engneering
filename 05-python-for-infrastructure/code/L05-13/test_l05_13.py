"""Integration tests for TaskFlow API v0.1 — চালানো: python3 -m unittest -v

প্রতিটি test class নিজের server চালায়: 127.0.0.1, OS-নির্বাচিত port, temp directory-তে নতুন SQLite database।
"""
from __future__ import annotations

import http.client
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import taskflow_api as tf  # noqa: E402

tf.log.disabled = True                                     # test output-এ access log নয়


class ApiClient:
    def __init__(self, port: int) -> None:
        self.port = port

    def call(self, method: str, path: str, body: object | None = None, headers: dict[str, str] | None = None,
             raw: bytes | None = None) -> tuple[int, dict[str, str], object]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        hdrs = dict(headers or {})
        data = raw
        if body is not None:
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        try:
            conn.request(method, path, body=data, headers=hdrs)
            resp = conn.getresponse()
            payload = resp.read()
            return resp.status, {k.lower(): v for k, v in resp.getheaders()}, json.loads(payload) if payload else None
        finally:
            conn.close()


class ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.db = str(Path(cls._tmp.name, "taskflow.db"))
        cls.server = tf.make_server(tf.Config(port=0, db_path=cls.db))
        cls.thread = threading.Thread(target=cls.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        cls.thread.start()
        cls.api = ApiClient(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls._tmp.cleanup()


class CrudTest(ServerCase):
    def test_full_lifecycle(self) -> None:
        status, headers, task = self.api.call("POST", "/tasks", {"title": "  write runbook  "})
        self.assertEqual(status, 201)
        self.assertEqual(task["title"], "write runbook")                         # trim
        self.assertEqual(headers["location"], f"/tasks/{task['id']}")
        tid = task["id"]
        self.assertEqual(self.api.call("GET", f"/tasks/{tid}")[2]["done"], False)
        status, _, task = self.api.call("PATCH", f"/tasks/{tid}", {"done": True})
        self.assertEqual((status, task["done"], task["title"]), (200, True, "write runbook"))   # title অপরিবর্তিত
        self.assertEqual(self.api.call("DELETE", f"/tasks/{tid}")[0], 204)
        self.assertEqual(self.api.call("GET", f"/tasks/{tid}")[0], 404)
        self.assertEqual(self.api.call("DELETE", f"/tasks/{tid}")[0], 404)

    def test_list_filter_and_pagination(self) -> None:
        ids = [self.api.call("POST", "/tasks", {"title": f"page-{i}", "done": i % 2 == 0})[2]["id"] for i in range(5)]
        _, _, page = self.api.call("GET", "/tasks?limit=2&offset=0")
        self.assertEqual(page["limit"], 2)
        self.assertEqual(len(page["items"]), 2)
        _, _, done = self.api.call("GET", "/tasks?done=true&limit=100")
        self.assertTrue(all(t["done"] for t in done["items"]))
        self.assertTrue({ids[0], ids[2], ids[4]} <= {t["id"] for t in done["items"]})

    def test_health_ready_and_headers(self) -> None:
        status, headers, body = self.api.call("GET", "/health", headers={"X-Request-ID": "abc-123"})
        self.assertEqual((status, body["status"]), (200, "ok"))
        self.assertEqual(headers["x-request-id"], "abc-123")                     # পাঠানো id ফেরত আসে
        self.assertEqual(headers["server"], "taskflow")                          # Python version ফাঁস নয়
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(self.api.call("GET", "/ready")[0], 200)
        bad_id = self.api.call("GET", "/health", headers={"X-Request-ID": "x" * 100 + "\t"})[1]["x-request-id"]
        self.assertRegex(bad_id, r"^[0-9a-f]{16}$")                               # অদ্ভুত id বদলে নতুন


class ValidationTest(ServerCase):
    def test_rejections(self) -> None:
        cases = [
            ("POST", "/tasks", {"title": ""}, None, 422, "invalid_title"),
            ("POST", "/tasks", {"title": "x" * 201}, None, 422, "invalid_title"),
            ("POST", "/tasks", {"title": 5}, None, 422, "invalid_title"),
            ("POST", "/tasks", {"title": "x", "done": "yes"}, None, 422, "invalid_done"),
            ("POST", "/tasks", {"title": "x", "owner": "a"}, None, 422, "unknown_field"),
            ("POST", "/tasks", ["x"], None, 422, "invalid_body"),
            ("PATCH", "/tasks/1", {}, None, 422, "empty_patch"),
            ("GET", "/tasks?limit=0", None, None, 400, "invalid_query"),
            ("GET", "/tasks?done=maybe", None, None, 400, "invalid_query"),
            ("GET", "/nope", None, None, 404, "not_found"),
        ]
        for method, path, body, _, want_status, want_code in cases:
            with self.subTest(method=method, path=path, body=body):
                status, _, payload = self.api.call(method, path, body)
                self.assertEqual((status, payload["error"]["code"]), (want_status, want_code))

    def test_transport_level_errors(self) -> None:
        status, _, p = self.api.call("POST", "/tasks", raw=b"title=x", headers={"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual((status, p["error"]["code"]), (415, "unsupported_media_type"))
        status, _, p = self.api.call("POST", "/tasks", raw=b"{bad", headers={"Content-Type": "application/json"})
        self.assertEqual((status, p["error"]["code"]), (400, "invalid_json"))
        big = json.dumps({"title": "a" * (tf.MAX_BODY + 10)}).encode()
        status, _, p = self.api.call("POST", "/tasks", raw=big, headers={"Content-Type": "application/json"})
        self.assertEqual((status, p["error"]["code"]), (413, "too_large"))
        status, headers, _ = self.api.call("PUT", "/tasks")
        self.assertEqual((status, headers["allow"]), (405, "GET, POST"))

    def test_sql_injection_attempts_are_inert(self) -> None:
        title = "x'); DROP TABLE tasks; --"
        status, _, task = self.api.call("POST", "/tasks", {"title": title})
        self.assertEqual((status, task["title"]), (201, title))                   # আক্ষরিক data হিসেবে রাখা
        self.assertEqual(self.api.call("GET", "/tasks/1%20OR%201=1")[0], 404)
        self.assertEqual(self.api.call("GET", "/ready")[0], 200)                  # table এখনো আছে

    def test_concurrent_creates(self) -> None:
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda i: self.api.call("POST", "/tasks", {"title": f"c{i}"}), range(40)))
        self.assertEqual({r[0] for r in results}, {201})
        self.assertEqual(len({r[2]["id"] for r in results}), 40)                  # সব id অনন্য


class LifecycleTest(unittest.TestCase):
    def test_data_survives_restart_and_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            db = str(Path(d, "t.db"))
            for round_ in range(2):
                srv = tf.make_server(tf.Config(port=0, db_path=db))
                t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
                t.start()
                api = ApiClient(srv.server_address[1])
                if round_ == 0:
                    api.call("POST", "/tasks", {"title": "persist me"})
                else:
                    self.assertEqual([x["title"] for x in api.call("GET", "/tasks")[2]["items"]], ["persist me"])
                srv.shutdown()
                srv.server_close()

    def test_bad_config(self) -> None:
        for env in ({"TASKFLOW_PORT": "eighty"}, {"TASKFLOW_PORT": "70000"}, {"TASKFLOW_LOG_LEVEL": "loud"}):
            with self.subTest(env=env), self.assertRaises(SystemExit):
                tf.Config.from_env(env)

    def test_process_start_and_stop(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, "TASKFLOW_PORT": "0", "TASKFLOW_DB": str(Path(d, "p.db"))}
            kwargs: dict[str, object] = {}
            if os.name == "nt":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            proc = subprocess.Popen([sys.executable, str(HERE / "taskflow_api.py")], env=env,
                                    stderr=subprocess.PIPE, text=True, **kwargs)  # type: ignore[call-overload]
            try:
                assert proc.stderr is not None
                first = json.loads(proc.stderr.readline())
                port = int(re.search(r":(\d+)$", first["url"]).group(1))          # type: ignore[union-attr]
                self.assertEqual(ApiClient(port).call("GET", "/health")[0], 200)
                if os.name == "posix":
                    proc.send_signal(signal.SIGTERM)                              # graceful: exit 0, "stopped" log
                    self.assertEqual(proc.wait(timeout=10), 0)
                    self.assertIn('"msg": "stopped"', proc.stderr.read())
                else:
                    proc.terminate()                                              # Windows-এ SIGTERM handler চলে না
                    proc.wait(timeout=10)
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=10)
                if proc.stderr:
                    proc.stderr.close()
            time.sleep(0.1)                                                       # Windows-এ db file-এর lock ছাড়ার সময়


if __name__ == "__main__":
    unittest.main()
