#!/usr/bin/env python3
"""WireGuard config linter — key format, AllowedIPs overlap, full-tunnel, MTU, keepalive, secret handling।

  python3 wg_lint.py sample-wg0.conf
  python3 wg_lint.py /etc/wireguard/wg0.conf     # sudo লাগবে; file-এ private key আছে — output-এ key কখনো ছাপা হয় না

Exit: 0 কোনো ERROR/WARN নেই, 1 finding আছে, 2 file পড়া/parse error।
"""
from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import os
import stat
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Section:
    kind: str                              # Interface | Peer
    line: int
    keys: dict[str, str] = field(default_factory=dict)


def parse(text: str) -> list[Section]:
    """wg-quick format: [Interface] একবার, [Peer] বহুবার — configparser duplicate section মানে না, তাই নিজে parse।"""
    sections: list[Section] = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            kind = line[1:-1].strip()
            if kind not in ("Interface", "Peer"):
                raise ValueError(f"line {n}: unknown section [{kind}]")
            sections.append(Section(kind, n))
            continue
        if not sections:
            raise ValueError(f"line {n}: key outside any section")
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(f"line {n}: expected Key = Value")
        sections[-1].keys[key.strip()] = value.strip()
    if sum(s.kind == "Interface" for s in sections) != 1:
        raise ValueError("config must have exactly one [Interface]")
    return sections


def valid_key(k: str) -> bool:
    """WireGuard key = ৩২ byte, base64-এ ৪৪ অক্ষর।"""
    try:
        return len(base64.b64decode(k, validate=True)) == 32
    except (binascii.Error, ValueError):
        return False


def nets(value: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    return [ipaddress.ip_network(x.strip(), strict=False) for x in value.split(",") if x.strip()]


def lint(sections: list[Section], path: Path | None = None) -> list[str]:
    out: list[str] = []
    iface = next(s for s in sections if s.kind == "Interface")
    peers = [s for s in sections if s.kind == "Peer"]

    pk = iface.keys.get("PrivateKey")
    if pk is None and "PostUp" not in iface.keys:
        out.append(f"ERROR line {iface.line}: [Interface] has no PrivateKey")
    elif pk is not None:
        if not valid_key(pk):
            out.append(f"ERROR line {iface.line}: PrivateKey is not a 32-byte base64 key")
        out.append("INFO  PrivateKey is inline: keep the file mode 600 and never commit it "
                   "(or load it from a file with PostUp = wg set %i private-key <path>)")
    if path is not None and os.name == "posix":
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o077:
            out.append(f"WARN  file mode {mode:o}: readable by group/others — chmod 600")
    if "Address" not in iface.keys:
        out.append(f"WARN  line {iface.line}: [Interface] has no Address")
    mtu = iface.keys.get("MTU")
    if mtu and int(mtu) > 1420:
        out.append(f"WARN  MTU {mtu} > 1420: may black-hole over IPv6 underlays or PPPoE (see L02-09)")

    seen_keys: dict[str, int] = {}
    owned: list[tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, int]] = []
    for p in peers:
        pub = p.keys.get("PublicKey", "")
        if not valid_key(pub):
            out.append(f"ERROR line {p.line}: [Peer] PublicKey missing or not a 32-byte base64 key")
        elif pub in seen_keys:
            out.append(f"ERROR line {p.line}: duplicate PublicKey (also at line {seen_keys[pub]})")
        else:
            seen_keys[pub] = p.line
        if pub and pub == pk:
            out.append(f"ERROR line {p.line}: peer PublicKey equals our PrivateKey — key pasted in the wrong place")
        allowed = nets(p.keys.get("AllowedIPs", ""))
        if not allowed:
            out.append(f"WARN  line {p.line}: peer has no AllowedIPs — no traffic will be routed to it")
        for n in allowed:
            if n.prefixlen == 0:
                out.append(f"INFO  line {p.line}: AllowedIPs {n} = full tunnel (all traffic via this peer)")
            for other, oline in owned:
                if n.version == other.version and n.overlaps(other) and n.prefixlen and other.prefixlen:
                    out.append(f"ERROR line {p.line}: AllowedIPs {n} overlaps {other} of peer at line {oline} "
                               "— WireGuard routes each address to exactly one peer")
            owned.append((n, p.line))
        if "Endpoint" in p.keys and "PersistentKeepalive" not in p.keys:
            out.append(f"INFO  line {p.line}: Endpoint set but no PersistentKeepalive — "
                       "behind NAT, inbound traffic stops after the NAT mapping expires (25 is common)")
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint a WireGuard (wg-quick) config without printing secrets.")
    ap.add_argument("config", type=Path)
    args = ap.parse_args(argv)
    try:
        sections = parse(args.config.read_text(encoding="utf-8"))
        findings = lint(sections, args.config)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for f in findings:
        print(f)
    peers = sum(s.kind == "Peer" for s in sections)
    bad = sum(not f.startswith("INFO") for f in findings)
    print(f"{peers} peer(s), {bad} error/warning(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
