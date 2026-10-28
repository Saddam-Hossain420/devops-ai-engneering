#!/usr/bin/env python3
"""fstab_lint.py — EC2-এ /etc/fstab-এর যে ভুলে instance boot-এ আটকে যায় বা EFS অস্থির হয় (offline)।

  python3 fstab_lint.py /etc/fstab
  python3 fstab_lint.py sample/fstab

EBS: Nitro instance-এ EBS volume `/dev/nvme1n1`… হিসেবে আসে, এবং ক্রম boot-ভেদে বদলাতে পারে — `/dev/xvdf`,
`/dev/sdf`, `/dev/nvmeXn1` নয়, `UUID=`/`LABEL=`। Data volume-এ `nofail` না থাকলে volume না পেলে boot emergency
mode-এ যায় — আর cloud-এ console keyboard নেই।
EFS: `_netdev` (network-এর পরে mount), `hard` (`soft` = নীরব data নষ্টের ঝুঁকি), AWS-এর সুপারিশ করা NFS option;
`efs` type (amazon-efs-utils)-এ `tls`।
Exit: 0 কোনো ERROR নেই, 1 আছে, 2 input error।
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SYSTEM_MOUNTS = {"/", "/boot", "/boot/efi", "swap", "none"}
RAW_DEVICE = re.compile(r"^/dev/(xvd[a-z]+|sd[a-z]+|nvme\d+n\d+)(p?\d+)?$")
EFS_HOST = re.compile(r"^(fs-[0-9a-f]+)(\.efs\.[a-z0-9-]+\.amazonaws\.com)?:")
NFS_RECOMMENDED = ("nfsvers=4.1", "rsize=1048576", "wsize=1048576", "hard", "timeo=600", "retrans=2", "noresvport")


def lint(text: str) -> list[tuple[int, str, str]]:
    out: list[tuple[int, str, str]] = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        f = line.split()
        if len(f) < 4:
            out.append((n, "ERROR", f"{len(f)} fields — need at least device, mountpoint, type, options"))
            continue
        dev, mnt, fstype, opts = f[0], f[1], f[2], f[3].split(",")
        if EFS_HOST.match(dev) or fstype == "efs":
            if "_netdev" not in opts and fstype == "efs":
                out.append((n, "ERROR", f"{mnt}: efs mount without _netdev — systemd cannot tell it needs the network"))
            elif "_netdev" not in opts:
                out.append((n, "WARN", f"{mnt}: no _netdev — systemd infers it from the nfs type, but AWS recommends "
                                       "it for EFS"))
            if "soft" in opts:
                out.append((n, "ERROR", f"{mnt}: 'soft' — on a timeout writes can fail silently; use 'hard'"))
            if fstype.startswith("nfs"):
                missing = [o for o in NFS_RECOMMENDED if o not in opts and not (o == "hard" and "soft" in opts)]
                if missing:
                    out.append((n, "WARN", f"{mnt}: NFS options missing {', '.join(missing)} (AWS-recommended set)"))
            if fstype == "efs" and "tls" not in opts:
                out.append((n, "WARN", f"{mnt}: efs mount without 'tls' — traffic in transit not encrypted"))
            if "nofail" not in opts:
                out.append((n, "INFO", f"{mnt}: consider 'nofail' so an EFS outage does not block boot"))
            continue
        if mnt in SYSTEM_MOUNTS:
            continue
        if RAW_DEVICE.match(dev):
            out.append((n, "ERROR", f"{mnt}: device name {dev} — on Nitro instances names/order can change; use UUID= "
                                    "(blkid) or LABEL="))
        if "nofail" not in opts:
            out.append((n, "ERROR", f"{mnt}: no 'nofail' — if this volume is missing the instance stops in emergency "
                                    "mode and never becomes reachable"))
    return out


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Lint /etc/fstab for EC2 (EBS/EFS).")
    ap.add_argument("fstab", type=Path)
    a = ap.parse_args(argv)
    try:
        findings = lint(a.fstab.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for n, lvl, msg in findings:
        print(f"line {n:<3} {lvl:<5}  {msg}")
    errors = sum(lvl == "ERROR" for _, lvl, _ in findings)
    print(f"{errors} error(s), {len(findings) - errors} other finding(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
