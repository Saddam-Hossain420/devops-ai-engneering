#!/usr/bin/env python3
"""SSH hardening audit — sshd configuration ও authorized_keys (read-only)।

sshd নিয়ম: একই keyword একাধিকবার থাকলে **প্রথম** মান কার্যকর (বেশিরভাগ keyword-এ)।
তাই Ubuntu-তে sshd_config-এর শুরুতে `Include /etc/ssh/sshd_config.d/*.conf` থাকায়
drop-in file মূল file-কে override করে। নির্ভরযোগ্য উপায়: `sudo sshd -T`-এর output audit করা।

Usage:
  sudo sshd -T > /tmp/sshd-effective.txt
  python3 ssh_audit.py sshd /tmp/sshd-effective.txt
  python3 ssh_audit.py keys ~/.ssh/authorized_keys
"""
from __future__ import annotations

import argparse
import base64
import re
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

SEVERITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


def parse_sshd(text: str) -> dict[str, str]:
    """keyword (lowercase) → প্রথম মান। Match block-এর পরের অংশ global নয় — বাদ।"""
    cfg: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition(" ") if " " in line else line.partition("\t")
        key = key.lower()
        if key == "match":
            break  # শর্তসাপেক্ষ setting — এই সরল audit global অংশ দেখে
        cfg.setdefault(key, value.strip())  # first value wins
    return cfg


def audit_sshd(cfg: dict[str, str]) -> list[tuple[str, str]]:
    f: list[tuple[str, str]] = []

    def val(k: str, default: str) -> str:
        return cfg.get(k, default).lower()

    if val("permitemptypasswords", "no") == "yes":
        f.append(("CRITICAL", "PermitEmptyPasswords yes — password ছাড়া login"))
    if val("permitrootlogin", "prohibit-password") == "yes":
        f.append(("HIGH", "PermitRootLogin yes — root password দিয়ে সরাসরি login"))
    elif val("permitrootlogin", "prohibit-password") in ("prohibit-password", "without-password"):
        f.append(("INFO", "PermitRootLogin prohibit-password — root key দিয়ে পারে; 'no' বিবেচনা করুন"))
    if val("passwordauthentication", "yes") == "yes":
        f.append(("HIGH", "PasswordAuthentication yes — brute-force ঝুঁকি; key-only করুন"))
    if val("kbdinteractiveauthentication", "no") == "yes":
        f.append(("MEDIUM", "KbdInteractiveAuthentication yes — password-এর বিকল্প পথ খোলা (MFA ছাড়া)"))
    if val("pubkeyauthentication", "yes") == "no":
        f.append(("HIGH", "PubkeyAuthentication no — key login বন্ধ"))
    if val("x11forwarding", "no") == "yes":
        f.append(("LOW", "X11Forwarding yes — server-এ সাধারণত দরকার নেই"))
    if val("allowagentforwarding", "yes") == "yes":
        f.append(("LOW", "AllowAgentForwarding yes — compromised server আপনার agent ব্যবহার করতে পারে"))
    tries = cfg.get("maxauthtries", "6")
    if tries.isdigit() and int(tries) > 4:
        f.append(("LOW", f"MaxAuthTries {tries} — ৩-৪ যথেষ্ট"))
    if not any(k in cfg for k in ("allowusers", "allowgroups")):
        f.append(("INFO", "AllowUsers/AllowGroups নেই — কে login করতে পারে সীমিত করুন"))
    return sorted(f, key=lambda x: SEVERITY[x[0]])


@dataclass(frozen=True)
class Key:
    line: int
    options: str
    keytype: str
    bits: int | None
    comment: str
    blob: str


def read_string(data: bytes, offset: int) -> tuple[bytes, int]:
    """SSH wire format: ৪-byte big-endian দৈর্ঘ্য + সেই পরিমাণ byte।"""
    if offset + 4 > len(data):
        raise ValueError("truncated key blob")
    (n,) = struct.unpack(">I", data[offset:offset + 4])
    end = offset + 4 + n
    if end > len(data):
        raise ValueError("truncated key blob")
    return data[offset + 4:end], end


def rsa_bits(blob_b64: str) -> int:
    data = base64.b64decode(blob_b64, validate=True)
    name, off = read_string(data, 0)
    if name != b"ssh-rsa":
        raise ValueError(f"not an RSA key: {name!r}")
    _e, off = read_string(data, off)
    n, _ = read_string(data, off)
    n = n.lstrip(b"\x00")  # mpint-এ sign-এর জন্য শুরুতে 0x00 থাকতে পারে
    return (len(n) - 1) * 8 + n[0].bit_length() if n else 0


KEY_RE = re.compile(r"(?:^|\s)(ssh-ed25519|ssh-rsa|ssh-dss|ecdsa-sha2-nistp\d+|sk-[\w@.-]+)\s+([A-Za-z0-9+/=]+)(?:\s+(.*))?$")


def parse_authorized_keys(text: str) -> list[Key]:
    keys = []
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = KEY_RE.search(line)
        if not m:
            raise ValueError(f"line {n}: no recognizable key")
        options = line[:m.start(1)].strip()
        bits = rsa_bits(m.group(2)) if m.group(1) == "ssh-rsa" else None
        keys.append(Key(n, options, m.group(1), bits, (m.group(3) or "").strip(), m.group(2)))
    return keys


def audit_keys(keys: list[Key]) -> list[tuple[str, str]]:
    f: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for k in keys:
        label = f"line {k.line} ({k.comment or 'no comment'})"
        if k.keytype == "ssh-dss":
            f.append(("HIGH", f"{label}: DSA key — আধুনিক OpenSSH-এ বাতিল; ed25519 দিয়ে বদলান"))
        if k.keytype == "ssh-rsa" and k.bits is not None:
            if k.bits < 2048:
                f.append(("HIGH", f"{label}: RSA {k.bits} bit — দুর্বল"))
            elif k.bits < 3072:
                f.append(("LOW", f"{label}: RSA {k.bits} bit — নতুন key হলে ed25519 বা RSA ≥3072"))
        if not k.comment:
            f.append(("LOW", f"{label}: comment নেই — key কার তা চেনা যায় না (access review কঠিন)"))
        if k.blob in seen:
            f.append(("MEDIUM", f"{label}: duplicate of line {seen[k.blob]}"))
        seen.setdefault(k.blob, k.line)
        if k.options:
            f.append(("INFO", f"{label}: options = {k.options}"))
    return sorted(f, key=lambda x: SEVERITY[x[0]])


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Audit sshd configuration or authorized_keys.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sshd").add_argument("file", type=Path)
    sub.add_parser("keys").add_argument("file", type=Path)
    args = p.parse_args(argv)
    try:
        text = args.file.read_text(encoding="utf-8")
        findings = audit_sshd(parse_sshd(text)) if args.cmd == "sshd" else audit_keys(parse_authorized_keys(text))
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for level, msg in findings:
        print(f"{level:8} {msg}")
    print("summary: " + "  ".join(f"{s}={sum(x[0] == s for x in findings)}" for s in SEVERITY))
    return 1 if any(x[0] in ("CRITICAL", "HIGH") for x in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
