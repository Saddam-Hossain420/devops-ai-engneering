"""Tests for tg_health.py ও hc_sim.py — চালানো: python3 -m unittest -v
hc_sim আসল local HTTP server-এর বিরুদ্ধে চলে (ছোট interval); tg_health হাতে তৈরি describe-* নমুনায়।"""
from __future__ import annotations

import io
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import hc_sim as hs  # noqa: E402
import tg_health as th  # noqa: E402

S = HERE / "sample"
TG = json.loads((S / "tg.json").read_text(encoding="utf-8"))["TargetGroups"][0]


class Toggle(BaseHTTPRequestHandler):
    status = 200

    def do_GET(self) -> None:  # noqa: N802 — http.server-এর নাম
        self.send_response(type(self).status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


class HcSimTest(unittest.TestCase):
    def test_state_machine(self) -> None:
        t = hs.Target("x")
        self.assertEqual([hs.step(t, True, "", 3, 2) for _ in range(3)], [None, None, "healthy"])
        self.assertEqual(hs.step(t, False, "", 3, 2), None)                       # একটি ব্যর্থতায় নয়
        self.assertEqual(hs.step(t, True, "", 3, 2), None)                        # streak ভাঙল
        self.assertEqual([hs.step(t, False, "", 3, 2) for _ in range(2)], [None, "unhealthy"])

    def test_against_real_server(self) -> None:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Toggle)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_address[1]}/health"
        try:
            Toggle.status = 200
            ev = hs.run([hs.Target(url)], 0.3, 0.25, 2, 2, {200}, 3, out=io.StringIO())
            self.assertEqual([e[2] for e in ev], ["healthy"])
            Toggle.status = 503                                                   # app চলছে, কিন্তু ভুল code
            target = hs.Target(url, state="healthy")
            ev = hs.run([target], 0.3, 0.25, 2, 2, {200}, 3, out=io.StringIO())
            self.assertEqual([(e[2], e[3]) for e in ev], [("unhealthy", "HTTP 503")])
            self.assertEqual(hs.probe(url, 0.5, {200, 503})[0], True)             # matcher বদলালে "healthy"
        finally:
            srv.shutdown()
            srv.server_close()


class TgHealthTest(unittest.TestCase):
    def test_settings(self) -> None:
        got = th.check_settings(TG, {"deregistration_delay.timeout_seconds": "5"}, 10)
        self.assertEqual(got[0], ("INFO", "detect a dead target in ≈90s, readmit a recovered one in ≈150s"))
        self.assertEqual(sum(lvl == "WARN" for lvl, _ in got), 3)
        fast = dict(TG, HealthCheckIntervalSeconds=10, UnhealthyThresholdCount=2, HealthCheckPath="/health")
        self.assertEqual([lvl for lvl, _ in th.check_settings(fast, {"deregistration_delay.timeout_seconds": "30"}, 10)],
                         ["INFO"])
        overlap = dict(fast, HealthCheckTimeoutSeconds=10)
        self.assertIn("overlap", th.check_settings(overlap, {}, None)[1][1])

    def test_explain(self) -> None:
        health = json.loads((S / "health.json").read_text(encoding="utf-8"))
        got = th.explain(health)
        self.assertEqual([lvl for lvl, _ in got], ["OK", "ERROR", "ERROR"])
        self.assertIn("security group", got[1][1])
        unknown = {"TargetHealthDescriptions": [{"Target": {"Id": "i-x"}, "TargetHealth": {
            "State": "unhealthy", "Reason": "Target.SomethingNew", "Description": "new reason"}}]}
        self.assertIn("new reason", th.explain(unknown)[0][1])                    # অজানা code-এ AWS-এর description


if __name__ == "__main__":
    unittest.main()
