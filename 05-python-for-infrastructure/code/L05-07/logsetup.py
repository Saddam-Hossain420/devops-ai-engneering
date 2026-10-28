#!/usr/bin/env python3
"""logsetup.py — ops tool-এর জন্য logging: এক লাইনে এক JSON (বা মানুষের পড়ার text), request id, secret redaction।

  from logsetup import setup_logging, request_context
  log = setup_logging("info", json_output=True)
  with request_context("req-42"):
      log.info("backup started", extra={"db": "orders", "size_mb": 120})

নিয়ম: log যায় stderr-এ (stdout ফলাফলের জন্য — L04-01); সময় UTC ISO-8601; exception-এ traceback একটি field-এ;
password/token/secret/Authorization-এর মান "***" (message-এ ও extra field-এ)।
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import re
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import IO

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

# LogRecord-এর নিজস্ব attribute — extra হিসেবে আলাদা করে দেখানোর দরকার নেই
_STD_ATTRS = frozenset(vars(logging.LogRecord("x", 0, "x", 0, "x", None, None))) | {"message", "asctime"}

SECRET_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|authorization)")
SECRET_IN_TEXT = [
    re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|\S+)"),
    re.compile(r"(?i)\b(authorization)(\s*:\s*)((?:bearer|basic)\s+\S+|\S+)"),
    re.compile(r"(?i)(://[^:/\s]+)(:)([^@/\s]+)(?=@)"),                 # scheme://user:PASSWORD@host
]


def redact_text(text: str) -> str:
    for pattern in SECRET_IN_TEXT:
        text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}***", text)
    return text


def redact_value(key: str, value: object) -> object:
    if SECRET_KEY.search(key):
        return "***"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact_value(str(k), v) for k, v in value.items()}
    return value


class ContextFilter(logging.Filter):
    """প্রতিটি record-এ বর্তমান request_id যোগ।"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class RedactFilter(logging.Filter):
    """Message (format করার পরে) ও extra field থেকে secret সরানো — handler-এর আগে, তাই সব output-এ প্রযোজ্য।"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage())
        record.args = None
        for key, value in list(vars(record).items()):
            if key not in _STD_ATTRS and key != "request_id":
                setattr(record, key, redact_value(key, value))
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for key, value in vars(record).items():
            if key not in _STD_ATTRS and key not in doc:
                doc[key] = value
        if record.exc_info:
            doc["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            doc["exc"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(doc, ensure_ascii=False, default=str)


class TextFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s")

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        return datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        extras = {k: v for k, v in vars(record).items() if k not in _STD_ATTRS and k != "request_id"}
        if extras:                                   # extra field traceback-এর আগে, একই লাইনে
            record.message += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        record.asctime = self.formatTime(record)
        line = self.formatMessage(record)
        if record.exc_info:
            line += "\n" + redact_text(self.formatException(record.exc_info))
        return line


def setup_logging(level: str = "info", json_output: bool = False, stream: IO[str] | None = None,
                  name: str = "ops") -> logging.Logger:
    """একটি named logger configure করে (root-এ হাত দেয় না) — বারবার ডাকলেও handler দ্বিগুণ হয় না।"""
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    for h in list(logger.handlers):
        logger.removeHandler(h)
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.addFilter(ContextFilter())
    handler.addFilter(RedactFilter())
    handler.setFormatter(JsonFormatter() if json_output else TextFormatter())
    logger.addHandler(handler)
    logger.propagate = False                      # root-এ আবার না যাওয়া — দ্বিগুণ লাইন নয়
    return logger


@contextlib.contextmanager
def request_context(rid: str | None = None) -> Iterator[str]:
    """`with request_context():` — ভেতরের সব log-এ একই request_id। Thread-এ পাঠাতে copy_context() লাগে।"""
    token = request_id.set(rid or uuid.uuid4().hex[:12])
    try:
        yield request_id.get()
    finally:
        request_id.reset(token)
