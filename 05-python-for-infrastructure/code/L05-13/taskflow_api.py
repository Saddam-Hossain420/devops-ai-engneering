#!/usr/bin/env python3
"""taskflow_api.py — TaskFlow API v0.1: continuous project-এর প্রথম সংস্করণ। শুধু standard library (http.server + sqlite3)।

  TASKFLOW_DB=/tmp/taskflow.db python3 taskflow_api.py            # http://127.0.0.1:8000
  curl -s -X POST localhost:8000/tasks -H 'Content-Type: application/json' -d '{"title": "write runbook"}'

Endpoint:
  GET    /health          liveness — process সাড়া দিচ্ছে
  GET    /ready           readiness — database ব্যবহারযোগ্য (না হলে 503)
  GET    /tasks           ?done=true|false&limit=1..100&offset=N
  POST   /tasks           {"title": "...", "done": false}            → 201 + Location
  GET    /tasks/{id}
  PATCH  /tasks/{id}      {"title"?: "...", "done"?: true}
  DELETE /tasks/{id}                                                  → 204

Configuration (env, L05-05/L05-10-এর নিয়ম): TASKFLOW_HOST (127.0.0.1), TASKFLOW_PORT (8000), TASKFLOW_DB
(taskflow.db), TASKFLOW_LOG_LEVEL (info)। প্রতিটি request-এর এক লাইন JSON log stderr-এ, X-Request-ID সহ।
SIGTERM/SIGINT → নতুন request নেওয়া বন্ধ, চলমান request শেষ, তারপর exit 0।

সতর্কতা: Python-এর http.server production-এর জন্য তৈরি নয় (documentation-এ স্পষ্ট বলা)। এখানে শেখার
জন্য সরল রাখা হয়েছে; Module 06-এ nginx সামনে বসবে, পরে production-মানের server/framework আসবে।
"""
from __future__ import annotations

import json
import logging
import os
import re
import signal
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

__version__ = "0.1.0"
MAX_BODY = 16 * 1024
MAX_DRAIN = 1024 * 1024        # 413-এর পরে বড়জোর এতটুকু body পড়ে ফেলা (তার বেশি হলে সরাসরি বন্ধ)
TITLE_MAX = 200
REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
TASK_PATH = re.compile(r"^/tasks/(\d{1,18})$")
SCHEMA_VERSION = 1

log = logging.getLogger("taskflow")


# ---------------- configuration ----------------

@dataclass(frozen=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = "taskflow.db"
    log_level: str = "info"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        env = dict(os.environ if env is None else env)
        try:
            port = int(env.get("TASKFLOW_PORT", "8000"))
        except ValueError:
            raise SystemExit(f"config error: TASKFLOW_PORT must be an integer, got {env['TASKFLOW_PORT']!r}") from None
        if not 0 <= port <= 65535:
            raise SystemExit(f"config error: TASKFLOW_PORT out of range: {port}")
        level = env.get("TASKFLOW_LOG_LEVEL", "info").lower()
        if level not in ("debug", "info", "warning", "error"):
            raise SystemExit(f"config error: TASKFLOW_LOG_LEVEL must be debug/info/warning/error, got {level!r}")
        return cls(env.get("TASKFLOW_HOST", "127.0.0.1"), port, env.get("TASKFLOW_DB", "taskflow.db"), level)


# ---------------- storage ----------------

class Store:
    """প্রতিটি কাজে নতুন sqlite connection — thread-গুলো connection ভাগ করে না।"""

    def __init__(self, path: str) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout = 5000")
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def migrate(self) -> None:
        with closing(self.connect()) as con, con:
            con.execute("PRAGMA journal_mode = WAL")                     # পাঠক ও লেখক একে অপরকে কম আটকায়
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise SystemExit(f"database schema v{version} is newer than this app (v{SCHEMA_VERSION})")
            if version < 1:
                con.execute("""CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
                    done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL)""")
                con.execute("PRAGMA user_version = 1")

    def ready(self) -> bool:
        try:
            with closing(self.connect()) as con:
                con.execute("SELECT 1 FROM tasks LIMIT 1").fetchall()
            return True
        except sqlite3.Error:
            return False

    @staticmethod
    def row(r: sqlite3.Row) -> dict[str, Any]:
        return {"id": r["id"], "title": r["title"], "done": bool(r["done"]),
                "created_at": r["created_at"], "updated_at": r["updated_at"]}

    def list(self, done: bool | None, limit: int, offset: int) -> tuple[list[dict[str, Any]], int]:
        # স্থির SQL: "?1 IS NULL" হলে filter নেই — f-string-এ query গড়ার দরকারই নেই
        flag = None if done is None else int(done)
        with closing(self.connect()) as con:
            total = con.execute("SELECT count(*) FROM tasks WHERE ?1 IS NULL OR done = ?1", (flag,)).fetchone()[0]
            rows = con.execute("SELECT * FROM tasks WHERE ?1 IS NULL OR done = ?1 ORDER BY id LIMIT ?2 OFFSET ?3",
                               (flag, limit, offset))
            return [self.row(r) for r in rows], total

    def get(self, task_id: int) -> dict[str, Any] | None:
        with closing(self.connect()) as con:
            r = con.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return self.row(r) if r else None

    def create(self, title: str, done: bool) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with closing(self.connect()) as con, con:
            cur = con.execute("INSERT INTO tasks (title, done, created_at, updated_at) VALUES (?, ?, ?, ?)",
                              (title, int(done), now, now))
            task_id = cur.lastrowid
        task = self.get(task_id) if task_id is not None else None
        if task is None:                                           # assert নয় — `python -O` দিলে assert মুছে যায়
            raise sqlite3.DatabaseError("inserted row not found")
        return task

    def update(self, task_id: int, changes: dict[str, Any]) -> dict[str, Any] | None:
        done = changes.get("done")
        now = datetime.now(UTC).isoformat(timespec="seconds")
        with closing(self.connect()) as con, con:                  # COALESCE: None = "বদলাবেন না"
            cur = con.execute("UPDATE tasks SET title = COALESCE(?, title), done = COALESCE(?, done), "
                              "updated_at = ? WHERE id = ?",
                              (changes.get("title"), None if done is None else int(done), now, task_id))
            if cur.rowcount == 0:
                return None
        return self.get(task_id)

    def delete(self, task_id: int) -> bool:
        with closing(self.connect()) as con, con:
            return con.execute("DELETE FROM tasks WHERE id = ?", (task_id,)).rowcount == 1


# ---------------- validation ----------------

class ApiError(Exception):
    def __init__(self, status: HTTPStatus, code: str, message: str, headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.headers = status, code, message, headers or {}


def validate_task(body: object, partial: bool) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_body", "JSON body must be an object")
    unknown = set(body) - {"title", "done"}
    if unknown:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "unknown_field", f"unknown field(s): {', '.join(sorted(unknown))}")
    out: dict[str, Any] = {}
    if "title" in body or not partial:
        title = body.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_title", "title must be a non-empty string")
        if len(title.strip()) > TITLE_MAX:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_title", f"title longer than {TITLE_MAX} characters")
        out["title"] = title.strip()
    if "done" in body:
        if not isinstance(body["done"], bool):                   # 1/"true" নয় — শুধু JSON true/false
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "invalid_done", "done must be true or false")
        out["done"] = body["done"]
    if partial and not out:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "empty_patch", "nothing to update")
    return out


def int_param(query: dict[str, list[str]], name: str, default: int, lo: int, hi: int) -> int:
    raw = query.get(name, [str(default)])[-1]
    if not raw.isdigit() or not lo <= int(raw) <= hi:
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_query", f"{name} must be an integer {lo}..{hi}")
    return int(raw)


# ---------------- HTTP ----------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    store: Store                                                 # make_server বসায়

    def version_string(self) -> str:                             # default: "BaseHTTP/0.6 Python/3.x" — version ফাঁস
        return "taskflow"

    # BaseHTTPRequestHandler নিজের access log stderr-এ লেখে — আমরা নিজের JSON log লিখি
    def log_message(self, fmt: str, *args: object) -> None:
        log.debug("http.server: " + fmt, *args)

    def _begin(self) -> None:
        self._start = time.monotonic()
        incoming = self.headers.get("X-Request-ID", "")
        self.request_id = incoming if REQUEST_ID.match(incoming) else uuid.uuid4().hex[:16]

    def _send(self, status: HTTPStatus, payload: object | None = None, headers: dict[str, str] | None = None) -> None:
        body = b"" if payload is None else (json.dumps(payload, ensure_ascii=False) + "\n").encode()
        self.send_response(status)
        self.send_header("X-Request-ID", self.request_id)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if payload is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)
        log.info("request", extra={"method": self.command, "path": urlsplit(self.path).path, "status": int(status),
                                   "duration_ms": round((time.monotonic() - self._start) * 1000, 2),
                                   "request_id": self.request_id, "client": self.client_address[0]})

    def _error(self, err: ApiError) -> None:
        self._send(err.status, {"error": {"code": err.code, "message": err.message, "request_id": self.request_id}},
                   err.headers)

    def _drain(self, length: int) -> None:
        """না-পড়া data রেখে socket বন্ধ করলে kernel RST পাঠায় — client তখন 413 উত্তরটাই হারাতে পারে।
        nginx-এর lingering close-এর মতো: সীমিত পরিমাণ (MAX_DRAIN, ১ সেকেন্ড পর্যন্ত) পড়ে ফেলে দেওয়া।"""
        left = min(length, MAX_DRAIN)
        self.connection.settimeout(1.0)
        try:
            while left > 0:
                chunk = self.rfile.read1(min(left, 65536))
                if not chunk:
                    break
                left -= len(chunk)
        except OSError:
            pass

    def _json_body(self) -> object:
        ctype = self.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ApiError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "unsupported_media_type", "Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            raise ApiError(HTTPStatus.LENGTH_REQUIRED, "length_required", "Content-Length header required") from None
        if length > MAX_BODY:
            self.close_connection = True                          # keep-alive নয় — connection বন্ধ হবে
            self._drain(length)
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "too_large", f"body larger than {MAX_BODY} bytes")
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", f"invalid JSON: {exc}") from None

    def _dispatch(self) -> None:
        self._begin()
        try:
            self._route()
        except ApiError as err:
            self._error(err)
        except sqlite3.Error:
            log.exception("database error", extra={"request_id": self.request_id})
            self._error(ApiError(HTTPStatus.SERVICE_UNAVAILABLE, "database_unavailable", "database error"))
        except Exception:                                         # traceback client-এ নয়, log-এ
            log.exception("unhandled error", extra={"request_id": self.request_id})
            self._error(ApiError(HTTPStatus.INTERNAL_SERVER_ERROR, "internal", "internal server error"))

    def _route(self) -> None:
        url = urlsplit(self.path)
        method, path = self.command, url.path.rstrip("/") or "/"
        if path == "/health" and method in ("GET", "HEAD"):
            return self._send(HTTPStatus.OK, {"status": "ok", "version": __version__})
        if path == "/ready" and method in ("GET", "HEAD"):
            ok = self.store.ready()
            return self._send(HTTPStatus.OK if ok else HTTPStatus.SERVICE_UNAVAILABLE,
                              {"status": "ready" if ok else "not ready"})
        if path == "/tasks":
            if method == "GET":
                q = parse_qs(url.query)
                done_raw = q.get("done", [None])[-1]
                if done_raw not in (None, "true", "false"):
                    raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_query", "done must be true or false")
                done = None if done_raw is None else done_raw == "true"
                limit = int_param(q, "limit", 50, 1, 100)
                offset = int_param(q, "offset", 0, 0, 10**9)
                items, total = self.store.list(done, limit, offset)
                return self._send(HTTPStatus.OK, {"items": items, "total": total, "limit": limit, "offset": offset})
            if method == "POST":
                data = validate_task(self._json_body(), partial=False)
                task = self.store.create(data["title"], data.get("done", False))
                return self._send(HTTPStatus.CREATED, task, {"Location": f"/tasks/{task['id']}"})
            raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", f"{method} not allowed on /tasks",
                           {"Allow": "GET, POST"})                # 405-এ Allow বাধ্যতামূলক (RFC 9110)
        m = TASK_PATH.match(path)
        if m:
            task_id = int(m.group(1))
            if method == "GET":
                task = self.store.get(task_id)
            elif method == "PATCH":
                task = self.store.update(task_id, validate_task(self._json_body(), partial=True))
            elif method == "DELETE":
                if not self.store.delete(task_id):
                    raise ApiError(HTTPStatus.NOT_FOUND, "not_found", f"task {task_id} not found")
                return self._send(HTTPStatus.NO_CONTENT)
            else:
                raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", f"{method} not allowed",
                               {"Allow": "GET, PATCH, DELETE"})
            if task is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "not_found", f"task {task_id} not found")
            return self._send(HTTPStatus.OK, task)
        raise ApiError(HTTPStatus.NOT_FOUND, "not_found", f"no route for {path}")

    do_GET = do_POST = do_PATCH = do_DELETE = do_HEAD = do_PUT = _dispatch    # noqa: N815


# ---------------- logging & server ----------------

class JsonFormatter(logging.Formatter):
    STD = frozenset(vars(logging.LogRecord("x", 0, "x", 0, "x", None, None))) | {"message"}

    def format(self, record: logging.LogRecord) -> str:
        doc: dict[str, object] = {"ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
                                  "level": record.levelname.lower(), "msg": record.getMessage()}
        doc.update({k: v for k, v in vars(record).items() if k not in self.STD})
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc, ensure_ascii=False, default=str)


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    log.handlers[:] = [handler]
    log.setLevel(level.upper())
    log.propagate = False


def make_server(cfg: Config) -> ThreadingHTTPServer:
    store = Store(cfg.db_path)
    store.migrate()
    handler = type("BoundHandler", (Handler,), {"store": store})
    server = ThreadingHTTPServer((cfg.host, cfg.port), handler)
    server.daemon_threads = False                     # shutdown-এ চলমান request শেষ হতে দেওয়া
    server.block_on_close = True
    return server


def main() -> int:
    cfg = Config.from_env()
    setup_logging(cfg.log_level)
    server = make_server(cfg)
    host, port = server.server_address[:2]
    log.info("listening", extra={"url": f"http://{host}:{port}", "db": str(Path(cfg.db_path)), "version": __version__})

    def stop(signum: int, _frame: object) -> None:
        log.info("shutdown requested", extra={"signal": signal.Signals(signum).name})
        threading.Thread(target=server.shutdown, daemon=True).start()     # serve_forever-এর thread থেকে নয়

    signal.signal(signal.SIGINT, stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()                         # block_on_close: চলমান request-এর thread join
        log.info("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
