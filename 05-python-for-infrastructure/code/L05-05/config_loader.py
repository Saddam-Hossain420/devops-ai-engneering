#!/usr/bin/env python3
"""config_loader.py — স্তরভিত্তিক configuration: default < file (JSON/TOML/YAML) < env var < CLI `--set`।

  python3 config_loader.py --config app.toml
  APP_SERVER__PORT=9000 python3 config_loader.py --config app.json --set log.level=debug --explain

প্রতিটি মান কোথা থেকে এসেছে (`--explain`) দেখায়; schema দিয়ে type, সীমা ও বাধ্যতামূলক key যাচাই;
JSON-এ duplicate key ধরা; secret-এর মান output-এ mask করা।
YAML শুধু PyYAML install থাকলে (না থাকলে স্পষ্ট error)।
Exit: 0 valid, 1 validation error, 2 file/parse error।
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ModuleNotFoundError:
    yaml = None

DEFAULTS: dict[str, Any] = {
    "server": {"host": "127.0.0.1", "port": 8080, "workers": 2},
    "log": {"level": "info", "json": False},
    "db": {"url": "sqlite:///taskflow.db", "password": None, "timeout_s": 5.0},
    "features": {"signup": True},
}


@dataclass(frozen=True)
class Rule:
    type: type
    required: bool = False
    choices: tuple[Any, ...] | None = None
    min: float | None = None
    max: float | None = None


SCHEMA: dict[str, Rule] = {
    "server.host": Rule(str, required=True),
    "server.port": Rule(int, required=True, min=1, max=65535),
    "server.workers": Rule(int, min=1, max=64),
    "log.level": Rule(str, choices=("debug", "info", "warning", "error")),
    "log.json": Rule(bool),
    "db.url": Rule(str, required=True),
    "db.password": Rule(str),
    "db.timeout_s": Rule(float, min=0.1, max=300),
    "features.signup": Rule(bool),
}
SECRET_WORDS = ("password", "secret", "token", "key")


class ConfigError(Exception):
    pass


# ---------- parsing ----------

def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in pairs:
        if k in out:
            raise ConfigError(f"duplicate key {k!r}")      # json.loads নিজে শেষেরটা নীরবে রাখে
        out[k] = v
    return out


def parse_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"{path}: {exc.strerror}") from None
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(text, object_pairs_hook=_no_duplicates)
        elif suffix == ".toml":
            data = tomllib.loads(text)
        elif suffix in (".yaml", ".yml"):
            if yaml is None:
                raise ConfigError("YAML needs PyYAML (pip install pyyaml in a venv); or use JSON/TOML")
            data = yaml.safe_load(text)                     # কখনো yaml.load নয়
        else:
            raise ConfigError(f"unsupported config type {suffix!r}")
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{path}:{exc.lineno}:{exc.colno}: {exc.msg}") from None
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from None
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from None
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping, got {type(data).__name__}")
    return data


def coerce(raw: str, rule: Rule | None, where: str = "") -> Any:
    """env/CLI-র string → schema-র type। bool-এ শুধু স্পষ্ট শব্দ গ্রহণ করা হয়।"""
    if rule is None or rule.type is str:
        return raw
    if rule.type is bool:
        low = raw.strip().lower()
        if low in ("true", "1", "yes", "on"):
            return True
        if low in ("false", "0", "no", "off"):
            return False
        raise ConfigError(f"{where}: expected bool, got {raw!r}")
    try:
        return rule.type(raw)
    except ValueError:
        raise ConfigError(f"{where}: expected {rule.type.__name__}, got {raw!r}") from None


# ---------- merging ----------

def flatten(d: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, Mapping):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def set_path(d: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        nxt = d.setdefault(p, {})
        if not isinstance(nxt, dict):
            raise ConfigError(f"{dotted}: {p!r} is not a section")
        d = nxt
    d[parts[-1]] = value


def env_overrides(environ: Mapping[str, str], prefix: str = "APP_") -> dict[str, str]:
    """APP_SERVER__PORT=9000 → server.port (double underscore = section)।"""
    return {k[len(prefix):].lower().replace("__", "."): v
            for k, v in environ.items() if k.startswith(prefix)}


def load(config_file: Path | None = None, environ: Mapping[str, str] | None = None,
         sets: list[str] | None = None) -> tuple[dict[str, Any], dict[str, str]]:
    """(config, source) — source[key] = 'default' / file নাম / 'env:NAME' / 'cli'।"""
    cfg = copy.deepcopy(DEFAULTS)
    source = {k: "default" for k in flatten(cfg)}
    if config_file is not None:
        for k, v in flatten(parse_file(config_file)).items():
            set_path(cfg, k, v)
            source[k] = config_file.name
    for k, raw in env_overrides(environ if environ is not None else os.environ).items():
        name = "APP_" + k.upper().replace(".", "__")
        set_path(cfg, k, coerce(raw, SCHEMA.get(k), f"env {name}"))
        source[k] = f"env:{name}"
    for item in sets or []:
        if "=" not in item:
            raise ConfigError(f"--set needs key=value, got {item!r}")
        k, raw = item.split("=", 1)
        set_path(cfg, k.strip(), coerce(raw, SCHEMA.get(k.strip()), f"--set {k.strip()}"))
        source[k.strip()] = "cli"
    return cfg, source


# ---------- validation ----------

def validate(cfg: Mapping[str, Any]) -> list[str]:
    flat = flatten(cfg)
    errors = [f"{k}: unknown key (typo?)" for k in flat if k not in SCHEMA]
    for key, rule in SCHEMA.items():
        value = flat.get(key)
        if value is None:
            if rule.required:
                errors.append(f"{key}: required")
            continue
        if isinstance(value, bool) and rule.type is not bool:      # bool হলো int-এর subclass
            ok_type = False
        elif rule.type is float:
            ok_type = isinstance(value, (int, float))
        else:
            ok_type = isinstance(value, rule.type)
        if not ok_type:
            errors.append(f"{key}: expected {rule.type.__name__}, got {type(value).__name__} {value!r}")
            continue
        if rule.choices and value not in rule.choices:
            errors.append(f"{key}: {value!r} not in {list(rule.choices)}")
        if rule.min is not None and value < rule.min:
            errors.append(f"{key}: {value} < min {rule.min}")
        if rule.max is not None and value > rule.max:
            errors.append(f"{key}: {value} > max {rule.max}")
    return errors


def masked(cfg: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in cfg.items():
        if isinstance(v, Mapping):
            out[k] = masked(v)
        else:
            out[k] = "***" if v is not None and any(w in k.lower() for w in SECRET_WORDS) else v
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Load layered configuration and validate it.")
    ap.add_argument("--config", type=Path)
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--explain", action="store_true", help="show where each value came from")
    args = ap.parse_args(argv)
    try:
        cfg, source = load(args.config, sets=args.set)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.explain:
        for k, v in flatten(masked(cfg)).items():
            print(f"{k:<18} = {json.dumps(v):<26} <- {source.get(k, '?')}")
    else:
        print(json.dumps(masked(cfg), indent=2))
    errors = validate(cfg)
    for e in errors:
        print(f"INVALID {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
