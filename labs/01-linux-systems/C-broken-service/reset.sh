#!/usr/bin/env bash
# Lab 01-C cleanup: break-it.sh যা তৈরি করেছিল সব মুছে ফেলে। আবার চালানো নিরাপদ।
# Usage: sudo bash reset.sh --yes-i-am-in-a-vm
set -uo pipefail

[[ "${1:-}" == "--yes-i-am-in-a-vm" ]] || { echo "refusing: run with --yes-i-am-in-a-vm" >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 2; }

systemctl disable --now lab-c.service 2>/dev/null
rm -f /etc/systemd/system/lab-c.service
rm -rf /etc/systemd/system/lab-c.service.d
systemctl daemon-reload
systemctl reset-failed lab-c.service 2>/dev/null
mountpoint -q /srv/lab-c/data && umount /srv/lab-c/data
rm -rf /srv/lab-c /etc/lab-c
id labc >/dev/null 2>&1 && userdel labc
echo "lab-c removed"
