#!/usr/bin/env python3
"""Layered environment configuration: base → environment file → environment variables.

Precedence (পরেরটি আগেরটিকে override করে):
  1. config/base.json          — সব environment-এর common default
  2. config/<env>.json         — শুধু যা এই environment-এ আলাদা
  3. APP_<SECTION>__<KEY> env var — runtime-এ (secret সবসময় এখান থেকে)

যেমন: APP_DATABASE__PASSWORD=...  →  config["database"]["password"]

Commands:
  python3 envconfig.py show prod           # final config (secret masked)
  python3 envconfig.py diff staging prod   # কোন key-এ দুই environment আলাদা
  python3 envconfig.py validate prod       # environment-এর নিয়ম যাচাই; fail হলে exit 1
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
CONFIG_DIR = HERE / "config"
ENVIRONMENTS = ("dev", "staging", "prod")
ENV_PREFIX = "APP_"
SECRET_WORDS = ("password", "secret", "token", "api_key")


def is_secret(key: str) -> bool:
    return any(word in key.lower() for word in SECRET_WORDS)


def deep_merge(base: dict, override: Mapping) -> dict:
    """Nested dict merge; override-এর মান জেতে। base অপরিবর্তিত থাকে।"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def parse_env_value(raw: str) -> Any:
    """'20' → 20, 'true' → True, অন্যথায় string। JSON parse দিয়ে type রক্ষা।"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def env_overrides(environ: Mapping[str, str]) -> dict:
    """APP_DATABASE__POOL_SIZE=20 → {"database": {"pool_size": 20}}."""
    result: dict = {}
    for name, raw in environ.items():
        if not name.startswith(ENV_PREFIX):
            continue
        path = [part.lower() for part in name[len(ENV_PREFIX):].split("__") if part]
        if not path:
            continue
        node = result
        for part in path[:-1]:
            node = node.setdefault(part, {})
        node[path[-1]] = parse_env_value(raw)
    return result


def find_secrets_in_files(data: Mapping, path: str = "") -> list[str]:
    """Config file-এ secret-এর মত key থাকলে তার path — file-এ secret রাখা নিষেধ।"""
    found: list[str] = []
    for key, value in data.items():
        here = f"{path}.{key}" if path else key
        if isinstance(value, Mapping):
            found += find_secrets_in_files(value, here)
        elif is_secret(key):
            found.append(here)
    return found


def load_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_config(env: str, environ: Mapping[str, str] | None = None,
                config_dir: Path = CONFIG_DIR) -> dict:
    if env not in ENVIRONMENTS:
        raise ValueError(f"unknown environment {env!r}; choose from {', '.join(ENVIRONMENTS)}")
    base = load_file(config_dir / "base.json")
    layer = load_file(config_dir / f"{env}.json")
    for name, data in (("base.json", base), (f"{env}.json", layer)):
        leaked = find_secrets_in_files(data)
        if leaked:
            raise ValueError(f"secret-like keys in {name}: {', '.join(leaked)} — use env vars")
    config = deep_merge(base, layer)
    config = deep_merge(config, env_overrides(os.environ if environ is None else environ))
    config["environment"] = env
    return config


def validate(config: Mapping) -> list[str]:
    """Environment-ভিত্তিক নিয়ম। খালি list = সব ঠিক।"""
    env = config["environment"]
    app, db = config.get("app", {}), config.get("database", {})
    errors: list[str] = []
    if not isinstance(app.get("port"), int) or not 1 <= app["port"] <= 65535:
        errors.append("app.port must be an integer 1-65535")
    if env in ("staging", "prod"):
        if not db.get("password"):
            errors.append("database.password must be set via APP_DATABASE__PASSWORD")
        if db.get("host") in ("localhost", "127.0.0.1"):
            errors.append(f"database.host must not be localhost in {env}")
    if env == "prod":
        if app.get("debug"):
            errors.append("app.debug must be false in prod")
        if app.get("log_level") == "debug":
            errors.append("app.log_level must not be debug in prod")
    return errors


def flatten(data: Mapping, path: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in data.items():
        here = f"{path}.{key}" if path else key
        if isinstance(value, Mapping):
            flat.update(flatten(value, here))
        else:
            flat[here] = value
    return flat


def masked(data: Mapping) -> dict:
    """Output-এ secret কখনো দেখানো হয় না।"""
    return {k: (masked(v) if isinstance(v, Mapping) else ("***" if is_secret(k) and v else v))
            for k, v in data.items()}


def diff(a: Mapping, b: Mapping) -> list[tuple[str, Any, Any]]:
    fa, fb = flatten(masked(a)), flatten(masked(b))
    missing = object()
    rows = []
    for key in sorted(set(fa) | set(fb)):
        va, vb = fa.get(key, missing), fb.get(key, missing)
        if va != vb:
            rows.append((key, "<missing>" if va is missing else va, "<missing>" if vb is missing else vb))
    return rows


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Layered environment configuration tool.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show").add_argument("env")
    d = sub.add_parser("diff")
    d.add_argument("env_a")
    d.add_argument("env_b")
    sub.add_parser("validate").add_argument("env")
    args = p.parse_args(argv)

    try:
        if args.cmd == "show":
            print(json.dumps(masked(load_config(args.env)), indent=2))
        elif args.cmd == "diff":
            rows = diff(load_config(args.env_a), load_config(args.env_b))
            print(f"{'key':28} {args.env_a:22} {args.env_b}")
            for key, va, vb in rows:
                print(f"{key:28} {json.dumps(va):22} {json.dumps(vb)}")
        else:
            errors = validate(load_config(args.env))
            for e in errors:
                print(f"FAIL  {e}")
            print(f"{args.env}: {'OK' if not errors else f'{len(errors)} problem(s)'}")
            return 1 if errors else 0
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
