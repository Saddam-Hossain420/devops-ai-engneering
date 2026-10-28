#!/usr/bin/env python3
"""harden_audit.py — Ubuntu server-এর hardening অবস্থা read-only যাচাই (কিছু বদলায় না, sudo ছাড়াও বেশিরভাগ চলে)।

  python3 harden_audit.py                         # আসল system (/)
  python3 harden_audit.py --root sample-root      # নমুনা directory tree (যেকোনো OS)
  python3 harden_audit.py --json

যাচাই:
  sshd   — effective মান (sshd-এর নিয়ম: প্রতিটি keyword-এর **প্রথম** পাওয়া মান জেতে; Include যেখানে আছে সেখানেই পড়া হয়)
  sysctl — /etc/sysctl.conf + /etc/sysctl.d/*.conf (আসল system-এ /proc/sys-এর চলমান মানও)
  ports  — `ss -ltnH`-এর output: সব interface-এ খোলা অপ্রত্যাশিত port
  users  — root ছাড়া UID 0
  updates — unattended-upgrades চালু কিনা
  nginx  — server_tokens, limit_req_zone
Exit: 0 সব ঠিক, 1 warning, 2 critical (monitoring রীতি)।
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

OK, WARNING, CRITICAL = 0, 1, 2
EXPECTED_PUBLIC_PORTS = {22, 80, 443}
SSHD_WANT = {"permitrootlogin": {"no", "prohibit-password"}, "passwordauthentication": {"no"},
             "kbdinteractiveauthentication": {"no"}, "x11forwarding": {"no"}, "permitemptypasswords": {"no"}}
SSHD_DEFAULTS = {"permitrootlogin": "prohibit-password", "passwordauthentication": "yes",
                 "kbdinteractiveauthentication": "yes", "x11forwarding": "no", "permitemptypasswords": "no",
                 "maxauthtries": "6"}
SYSCTL_WANT = {"net.ipv4.conf.all.accept_redirects": "0", "net.ipv4.conf.all.send_redirects": "0",
               "net.ipv4.conf.all.rp_filter": ("1", "2"), "net.ipv4.tcp_syncookies": "1",
               "kernel.kptr_restrict": ("1", "2"), "kernel.dmesg_restrict": "1",
               "fs.protected_symlinks": "1", "fs.protected_hardlinks": "1", "net.ipv4.ip_forward": "0"}


@dataclass
class Finding:
    area: str
    status: int
    item: str
    detail: str


def read(root: Path, rel: str) -> str | None:
    try:
        return (root / rel.lstrip("/")).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def sshd_effective(root: Path, rel: str = "etc/ssh/sshd_config", seen: dict[str, tuple[str, str]] | None = None,
                   depth: int = 0) -> dict[str, tuple[str, str]]:
    """keyword → (মান, কোন file:line থেকে)। প্রথমটি জেতে; Include তার অবস্থানেই expand হয়। Match block-এর পরে থামি।"""
    seen = {} if seen is None else seen
    text = read(root, rel)
    if text is None or depth > 5:
        return seen
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        key, _, value = line.partition(" ")
        key, value = key.lower(), value.strip()
        if key == "match":
            break                                            # Match-এর পরের মান শর্তসাপেক্ষ — global হিসাবে নয়
        if key == "include":
            for pattern in value.split():
                full = pattern if pattern.startswith("/") else f"/etc/ssh/{pattern}"
                for path in sorted(glob.glob(str(root / full.lstrip("/")))):
                    sshd_effective(root, Path(path).relative_to(root).as_posix(), seen, depth + 1)
            continue
        seen.setdefault(key, (value.lower(), f"{rel}:{n}"))
    return seen


def audit_sshd(root: Path) -> list[Finding]:
    eff = sshd_effective(root)
    if not eff:
        return [Finding("sshd", WARNING, "sshd_config", "not readable / not present")]
    out = []
    for key, allowed in SSHD_WANT.items():
        value, where = eff.get(key, (SSHD_DEFAULTS[key], "built-in default"))
        status = OK if value in allowed else CRITICAL if key in ("passwordauthentication", "permitrootlogin",
                                                                   "permitemptypasswords") else WARNING
        out.append(Finding("sshd", status, key, f"{value}  ← {where}"))
    tries, where = eff.get("maxauthtries", (SSHD_DEFAULTS["maxauthtries"], "built-in default"))
    out.append(Finding("sshd", OK if int(tries) <= 4 else WARNING, "maxauthtries", f"{tries}  ← {where}"))
    return out


def sysctl_values(root: Path, live: bool) -> dict[str, tuple[str, str]]:
    values: dict[str, tuple[str, str]] = {}
    files = ["etc/sysctl.conf", *sorted(Path(p).relative_to(root).as_posix() for p in glob.glob(str(root / "etc/sysctl.d/*.conf")))]
    for rel in files:                                        # পরের file আগেরটাকে ছাপিয়ে যায় (sysctl --system)
        for n, raw in enumerate((read(root, rel) or "").splitlines(), 1):
            line = raw.split("#", 1)[0].split(";", 1)[0].strip()
            if "=" in line:
                k, v = (x.strip() for x in line.split("=", 1))
                values[k] = (v, f"{rel}:{n}")
    if live:
        for key in SYSCTL_WANT:
            proc = Path("/proc/sys") / key.replace(".", "/")
            try:
                values[key] = (proc.read_text().strip(), "running kernel")
            except OSError:
                pass
    return values


def audit_sysctl(root: Path, live: bool) -> list[Finding]:
    vals = sysctl_values(root, live)
    out = []
    for key, want in SYSCTL_WANT.items():
        wanted = want if isinstance(want, tuple) else (want,)
        if key not in vals:
            out.append(Finding("sysctl", WARNING, key, f"not set (want {'/'.join(wanted)}; kernel default applies)"))
            continue
        v, where = vals[key]
        out.append(Finding("sysctl", OK if v in wanted else WARNING, key, f"{v} (want {'/'.join(wanted)})  ← {where}"))
    return out


def audit_ports(ss_output: str | None) -> list[Finding]:
    if ss_output is None:
        return [Finding("ports", WARNING, "ss", "no `ss -ltnH` output available")]
    out = []
    for line in ss_output.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        addr, _, port = local.rpartition(":")
        if not port.isdigit():
            continue
        public = addr in ("0.0.0.0", "*", "[::]", "::")
        p = int(port)
        if public and p not in EXPECTED_PUBLIC_PORTS:
            out.append(Finding("ports", CRITICAL if p in (5432, 3306, 6379, 27017, 9200, 11211) else WARNING,
                               local, "listening on all interfaces — bind to 127.0.0.1 or firewall it"))
        else:
            out.append(Finding("ports", OK, local, "expected" if public else "local only"))
    return out


def audit_users(root: Path) -> list[Finding]:
    text = read(root, "etc/passwd") or ""
    zero = [line.split(":")[0] for line in text.splitlines() if line.count(":") >= 3 and line.split(":")[2] == "0"]
    extra = [u for u in zero if u != "root"]
    if extra:
        return [Finding("users", CRITICAL, "uid0", f"UID 0 besides root: {', '.join(extra)}")]
    return [Finding("users", OK, "uid0", "only root has UID 0")]


def audit_updates(root: Path) -> list[Finding]:
    text = read(root, "etc/apt/apt.conf.d/20auto-upgrades")
    if text is None:
        return [Finding("updates", WARNING, "unattended-upgrades", "20auto-upgrades not found")]
    on = re.search(r'APT::Periodic::Unattended-Upgrade\s+"1"', text)
    return [Finding("updates", OK if on else WARNING, "unattended-upgrades", "enabled" if on else "disabled")]


def audit_nginx(root: Path) -> list[Finding]:
    texts = [read(root, "etc/nginx/nginx.conf") or ""]
    texts += [Path(p).read_text(encoding="utf-8", errors="replace") for pattern in
              ("etc/nginx/conf.d/*.conf", "etc/nginx/sites-enabled/*") for p in glob.glob(str(root / pattern))]
    blob = "\n".join(re.sub(r"#.*", "", t) for t in texts)                  # comment-করা লাইন গোনা নয়
    if not blob.strip():
        return []
    return [Finding("nginx", OK if re.search(r"server_tokens\s+off", blob) else WARNING, "server_tokens",
                    "off" if re.search(r"server_tokens\s+off", blob) else "not 'off' — version shown in errors/headers"),
            Finding("nginx", OK if "limit_req_zone" in blob else WARNING, "limit_req_zone",
                    "rate limiting configured" if "limit_req_zone" in blob else "no rate limiting (login/API abuse)")]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Read-only hardening audit.")
    ap.add_argument("--root", type=Path, default=Path("/"))
    ap.add_argument("--ss-file", type=Path, help="saved `ss -ltnH` output (default: run ss, or ROOT/ss-ltnH.txt)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    live = a.root.resolve() == Path("/").resolve() and os.name == "posix"
    if a.ss_file:
        ss = a.ss_file.read_text(encoding="utf-8")
    elif (a.root / "ss-ltnH.txt").is_file():
        ss = (a.root / "ss-ltnH.txt").read_text(encoding="utf-8")
    elif live:
        r = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True)
        ss = r.stdout if r.returncode == 0 else None
    else:
        ss = None
    findings = (audit_sshd(a.root) + audit_sysctl(a.root, live) + audit_ports(ss) + audit_users(a.root)
                + audit_updates(a.root) + audit_nginx(a.root))
    worst = max((f.status for f in findings), default=OK)
    if a.json:
        print(json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False))
    else:
        label = {OK: "ok  ", WARNING: "WARN", CRITICAL: "CRIT"}
        for f in findings:
            print(f"{label[f.status]} {f.area:<8} {f.item:<38} {f.detail}")
        print(f"summary: {sum(f.status == CRITICAL for f in findings)} critical, "
              f"{sum(f.status == WARNING for f in findings)} warning, {sum(f.status == OK for f in findings)} ok")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
