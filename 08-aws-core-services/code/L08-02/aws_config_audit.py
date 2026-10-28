#!/usr/bin/env python3
"""aws_config_audit.py — ~/.aws/config ও ~/.aws/credentials পড়ে ঝুঁকি ও ভুল দেখায়; কোনো secret ছাপে না, কোনো API call নেই।

  python3 aws_config_audit.py                         # ~/.aws/ (বা AWS_CONFIG_FILE / AWS_SHARED_CREDENTIALS_FILE)
  python3 aws_config_audit.py --config sample/config --credentials sample/credentials
  python3 aws_config_audit.py --which deployer        # এই profile-এ CLI কোন ধরনের credential পাবে (সরল মডেল)

খোঁজে: দীর্ঘমেয়াদি key (AKIA…) · session token ছাড়া অস্থায়ী key (ASIA…) · region নেই · role profile-এর
source নেই/ভুল/চক্র · অসম্পূর্ণ SSO profile · credentials file অন্যরা পড়তে পারে (POSIX) · env-এ key (profile-কে চাপা দেয়)।
Exit: 0 কোনো ERROR নেই, 1 ERROR আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import configparser
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"


@dataclass
class Finding:
    level: str
    profile: str
    message: str


def mask(key_id: str) -> str:
    return key_id[:4] + "…" + key_id[-4:] if len(key_id) > 8 else "…"


def read_ini(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(interpolation=None)
    if path.is_file():
        cp.read(path, encoding="utf-8")
    return cp


def profiles_of(config: configparser.ConfigParser) -> dict[str, dict[str, str]]:
    """config-এ `[default]` ও `[profile NAME]`; `[sso-session X]` আলাদা।"""
    out = {}
    for section in config.sections():
        if section == "default":
            out["default"] = dict(config[section])
        elif section.startswith("profile "):
            out[section[len("profile "):].strip()] = dict(config[section])
    return out


def sso_sessions_of(config: configparser.ConfigParser) -> set[str]:
    return {s[len("sso-session "):].strip() for s in config.sections() if s.startswith("sso-session ")}


def kind_of(name: str, profiles: dict[str, dict[str, str]], creds: dict[str, dict[str, str]]) -> str:
    p = profiles.get(name, {})
    if "role_arn" in p:
        return "assume-role"
    if "sso_session" in p or "sso_start_url" in p:
        return "sso"
    keys = creds.get(name, {}) | {k: v for k, v in p.items() if k.startswith("aws_")}
    key_id = keys.get("aws_access_key_id", "")
    if key_id.startswith("ASIA"):
        return "temporary-keys"
    if key_id:
        return "long-lived-keys"
    if "credential_process" in p:
        return "credential-process"
    return "none"


def audit(profiles: dict[str, dict[str, str]], creds: dict[str, dict[str, str]], sso_sessions: set[str]) -> list[Finding]:
    out: list[Finding] = []
    for name in sorted(set(profiles) | set(creds)):
        p = profiles.get(name, {})
        keys = creds.get(name, {}) | {k: v for k, v in p.items() if k.startswith("aws_")}
        key_id = keys.get("aws_access_key_id", "")
        if key_id.startswith("AKIA"):
            out.append(Finding(WARN, name, f"long-lived access key {mask(key_id)} — prefer SSO or an assumed role"))
        elif key_id.startswith("ASIA") and not keys.get("aws_session_token"):
            out.append(Finding(ERROR, name, f"temporary key {mask(key_id)} without aws_session_token — every call will fail"))
        if any(k.startswith("aws_secret") for k in p):
            out.append(Finding(WARN, name, "secret stored in the config file — keep secrets only in credentials (or better, none)"))
        if "role_arn" in p:
            src = p.get("source_profile")
            if not src and not p.get("credential_source"):
                out.append(Finding(ERROR, name, "role_arn without source_profile or credential_source"))
            elif src and src not in profiles and src not in creds:
                out.append(Finding(ERROR, name, f"source_profile '{src}' does not exist"))
            elif src:
                seen, cur = {name}, src
                while cur and "role_arn" in profiles.get(cur, {}):
                    if cur in seen:
                        out.append(Finding(ERROR, name, f"source_profile chain loops back to '{cur}'"))
                        break
                    seen.add(cur)
                    cur = profiles[cur].get("source_profile", "")
            if "mfa_serial" in p:
                out.append(Finding(INFO, name, "role requires MFA (mfa_serial) — good for powerful roles"))
        if "sso_session" in p:
            if p["sso_session"] not in sso_sessions:
                out.append(Finding(ERROR, name, f"sso_session '{p['sso_session']}' has no [sso-session] section"))
            missing = [k for k in ("sso_account_id", "sso_role_name") if not p.get(k)]
            if missing:
                out.append(Finding(ERROR, name, "SSO profile missing " + ", ".join(missing)))
        if name in profiles and not p.get("region"):
            # named profile [default]-এর region পায় না — env (AWS_REGION/AWS_DEFAULT_REGION) না থাকলে command ব্যর্থ
            out.append(Finding(WARN, name, "no region — not inherited from [default]; uses AWS_REGION/AWS_DEFAULT_REGION "
                                           "or fails"))
    return out


def which(name: str | None, env: dict[str, str], profiles: dict[str, dict[str, str]], creds: dict[str, dict[str, str]]) -> str:
    """AWS CLI user guide-এর precedence-এর সরল রূপ: --profile → env-এর key → AWS_PROFILE → default।"""
    if name:
        return f"--profile {name}: {kind_of(name, profiles, creds)}"
    if env.get("AWS_ACCESS_KEY_ID"):
        kind = "temporary-keys" if env["AWS_ACCESS_KEY_ID"].startswith("ASIA") else "long-lived-keys"
        return f"environment variables: {kind} (these win over AWS_PROFILE and the files)"
    chosen = env.get("AWS_PROFILE", "default")
    return f"profile {chosen}: {kind_of(chosen, profiles, creds)}"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    home = Path.home() / ".aws"
    ap = argparse.ArgumentParser(description="Audit AWS CLI config/credentials files (no secrets printed, no API calls).")
    ap.add_argument("--config", type=Path, default=Path(os.environ.get("AWS_CONFIG_FILE", home / "config")))
    ap.add_argument("--credentials", type=Path,
                    default=Path(os.environ.get("AWS_SHARED_CREDENTIALS_FILE", home / "credentials")))
    ap.add_argument("--which", nargs="?", const="", metavar="PROFILE")
    a = ap.parse_args(argv)
    try:
        config, credfile = read_ini(a.config), read_ini(a.credentials)
    except configparser.Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    profiles = profiles_of(config)
    creds = {s: dict(credfile[s]) for s in credfile.sections()}
    if a.which is not None:
        print(which(a.which or None, dict(os.environ), profiles, creds))
        return 0
    findings = audit(profiles, creds, sso_sessions_of(config))
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        findings.append(Finding(WARN, "(env)", f"AWS_ACCESS_KEY_ID {mask(os.environ['AWS_ACCESS_KEY_ID'])} is set — "
                                               "it overrides AWS_PROFILE and the files unless --profile is given"))
    if os.name == "posix" and a.credentials.is_file() and a.credentials.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH):
        findings.append(Finding(WARN, "(file)", f"{a.credentials} is readable by group/others — chmod 600"))
    for f in sorted(findings, key=lambda f: ({ERROR: 0, WARN: 1, INFO: 2}[f.level], f.profile)):
        print(f"{f.level:<5}  {f.profile:<20} {f.message}")
    errors = sum(f.level == ERROR for f in findings)
    print(f"{len(profiles)} profile(s), {len(creds)} credential section(s): {errors} error(s), "
          f"{sum(f.level == WARN for f in findings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
