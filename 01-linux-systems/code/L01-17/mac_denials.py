#!/usr/bin/env python3
"""AppArmor ও SELinux denial বিশ্লেষণ — audit/kernel log থেকে গ্রুপ করে পরবর্তী পদক্ষেপ সুপারিশ।

Input (read-only):
  Ubuntu (AppArmor):  sudo journalctl -k --since today | grep -i apparmor > mac.log
  Fedora (SELinux):   sudo ausearch -m avc -ts today > mac.log      (বা /var/log/audit/audit.log)

Usage:
  python3 mac_denials.py mac.log
সিদ্ধান্ত মানুষের: tool শুধু সম্ভাব্য পথ দেখায় — কখনো "MAC বন্ধ করো" নয়।
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

KV_RE = re.compile(r'(\w+)=("([^"]*)"|\S+)')
AVC_RE = re.compile(r"avc:\s+(?P<result>denied|granted)\s+\{\s*(?P<perms>[^}]+?)\s*\}")

# SELinux: (source type, permission/class) → সম্ভাব্য boolean (Fedora/RHEL-এর পরিচিত কয়েকটি)
BOOLEAN_HINTS = {
    ("httpd_t", "name_connect"): "httpd_can_network_connect (বা DB হলে httpd_can_network_connect_db)",
    ("httpd_t", "sendto"): "httpd_can_sendmail",
}
WRONG_FILE_TYPES = {"user_home_t", "admin_home_t", "default_t", "tmp_t", "var_t", "unlabeled_t"}


@dataclass(frozen=True)
class Denial:
    system: str        # apparmor / selinux
    mode: str          # enforced / complain / permissive
    subject: str       # AppArmor profile বা SELinux source type
    action: str        # operation বা permission
    target: str        # path/name বা target type
    tclass: str
    comm: str


def kv(line: str) -> dict[str, str]:
    return {m.group(1): (m.group(3) if m.group(3) is not None else m.group(2)) for m in KV_RE.finditer(line)}


def selinux_type(context: str) -> str:
    """'system_u:system_r:httpd_t:s0' → 'httpd_t'."""
    parts = context.split(":")
    return parts[2] if len(parts) >= 3 else context


def parse_line(line: str) -> Denial | None:
    if 'apparmor="DENIED"' in line or 'apparmor="ALLOWED"' in line:
        f = kv(line)
        mode = "enforced" if f.get("apparmor") == "DENIED" else "complain"
        return Denial("apparmor", mode, f.get("profile", "?"), f.get("operation", "?"),
                      f.get("name", f.get("peer", "?")), f.get("class", "?"), f.get("comm", "?"))
    m = AVC_RE.search(line)
    if m and m["result"] == "denied":
        f = kv(line)
        mode = "permissive" if f.get("permissive") == "1" else "enforced"
        port = f.get("dest") or f.get("src")  # connect-এ dest=, bind-এ src=
        target = f.get("name") or (f"port {port}" if port else "?")
        return Denial("selinux", mode, selinux_type(f.get("scontext", "?")), m["perms"].strip(),
                      f"{target} ({selinux_type(f.get('tcontext', '?'))})", f.get("tclass", "?"),
                      f.get("comm", "?"))
    return None


def suggest(d: Denial) -> str:
    if d.system == "apparmor":
        return (f"profile '{d.subject}' {d.action} নিষেধ করছে '{d.target}' — path কি প্রত্যাশিত? "
                f"হলে profile/local override-এ নিয়ম যোগ (aa-logprof বা /etc/apparmor.d/local/)")
    target_type = d.target.rsplit("(", 1)[-1].rstrip(")")
    for (src, perm), boolean in BOOLEAN_HINTS.items():
        if d.subject == src and perm in d.action.split():
            return f"boolean দেখুন: getsebool {boolean.split()[0]} — চালু করতে setsebool -P (কারণ বুঝে)"
    if d.tclass == "file" or d.tclass == "dir":
        if target_type in WRONG_FILE_TYPES:
            return (f"file-এর label '{target_type}' — সম্ভবত ভুল জায়গা থেকে move/copy; "
                    f"restorecon -Rv PATH, স্থায়ী হলে semanage fcontext")
    if d.tclass in ("tcp_socket", "udp_socket") and "name_bind" in d.action:
        return "অস্বাভাবিক port — semanage port -a -t <type>_port_t -p tcp PORT"
    return "audit2why দিয়ে কারণ দেখুন; audit2allow শেষ উপায় — নিয়ম পড়ে বুঝে"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Summarize AppArmor/SELinux denials.")
    p.add_argument("log", type=Path)
    args = p.parse_args(argv)
    try:
        lines = args.log.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        print(f"error: file not found: {args.log}", file=sys.stderr)
        return 2
    denials = [d for d in map(parse_line, lines) if d]
    if not denials:
        print("no AppArmor/SELinux denials found")
        return 0
    groups = Counter(denials)
    for d, n in groups.most_common():
        print(f"{n:>3}× [{d.system}/{d.mode}] {d.comm}: {d.subject} — {d.action} {d.tclass} → {d.target}")
        print(f"      next: {suggest(d)}")
    enforced = sum(n for d, n in groups.items() if d.mode == "enforced")
    print(f"\n{len(denials)} denial(s), {len(groups)} unique, {enforced} enforced (actually blocked)")
    return 1 if enforced else 0


if __name__ == "__main__":
    raise SystemExit(main())
